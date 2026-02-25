# 02 - Data Models and Schemas

## Overview

The Spring Petclinic microservices use **separate databases per service** (database-per-service pattern). Each business service owns its data:

| Service | Database | Tables |
|---|---|---|
| customers-service | `petclinic` (customers) | `owners`, `pets`, `types` |
| vets-service | `petclinic` (vets) | `vets`, `specialties`, `vet_specialties` |
| visits-service | `petclinic` (visits) | `visits` |

Default database: **HSQLDB** (in-memory, for development). Production: **MySQL**. Python rewrite: **SQLite** (dev) / **PostgreSQL** (prod).

## Entity Relationship Diagram

```mermaid
erDiagram
    OWNERS ||--o{ PETS : "has"
    TYPES ||--o{ PETS : "categorizes"
    VETS }o--o{ SPECIALTIES : "has"
    PETS ||--o{ VISITS : "has"

    OWNERS {
        int id PK "AUTO_INCREMENT"
        varchar first_name "VARCHAR(30), NOT BLANK"
        varchar last_name "VARCHAR(30), NOT BLANK"
        varchar address "VARCHAR(255), NOT BLANK"
        varchar city "VARCHAR(80), NOT BLANK"
        varchar telephone "VARCHAR(12), NOT BLANK, digits only"
    }

    PETS {
        int id PK "AUTO_INCREMENT"
        varchar name "VARCHAR(30)"
        date birth_date "DATE"
        int type_id FK "NOT NULL -> types.id"
        int owner_id FK "NOT NULL -> owners.id"
    }

    TYPES {
        int id PK "AUTO_INCREMENT"
        varchar name "VARCHAR(80)"
    }

    VETS {
        int id PK "AUTO_INCREMENT"
        varchar first_name "VARCHAR(30), NOT BLANK"
        varchar last_name "VARCHAR(30), NOT BLANK"
    }

    SPECIALTIES {
        int id PK "AUTO_INCREMENT"
        varchar name "VARCHAR(80)"
    }

    VET_SPECIALTIES {
        int vet_id FK "NOT NULL -> vets.id"
        int specialty_id FK "NOT NULL -> specialties.id"
    }

    VISITS {
        int id PK "AUTO_INCREMENT"
        int pet_id "NOT NULL (logical FK, cross-service)"
        date visit_date "DATE/TIMESTAMP"
        varchar description "VARCHAR(8192)"
    }
```

**Important:** The `visits.pet_id` is a **logical foreign key** -- it references `pets.id` in the customers-service database, but there is no physical FK constraint since they are in separate databases. The MySQL schema for visits includes `FOREIGN KEY (pet_id) REFERENCES pets(id)` which only works when all tables share one database; in the microservice deployment, this constraint is not enforced at the DB level.

## 1. Customers Service Entities

### 1.1 Owner Entity

**Source:** `spring-petclinic-customers-service/src/main/java/.../model/Owner.java`

```java
@Entity
@Table(name = "owners")
public class Owner {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name = "first_name")
    @NotBlank
    private String firstName;

    @Column(name = "last_name")
    @NotBlank
    private String lastName;

    @Column(name = "address")
    @NotBlank
    private String address;

    @Column(name = "city")
    @NotBlank
    private String city;

    @Column(name = "telephone")
    @NotBlank
    @Digits(fraction = 0, integer = 12)
    private String telephone;

    @OneToMany(cascade = CascadeType.ALL, fetch = FetchType.EAGER, mappedBy = "owner")
    private Set<Pet> pets;
}
```

**Validation rules:**
- `firstName`: must not be blank
- `lastName`: must not be blank
- `address`: must not be blank
- `city`: must not be blank
- `telephone`: must not be blank, max 12 digits, no fractional part (digits-only string)

**Relationships:**
- One Owner has many Pets (`@OneToMany`, cascade ALL, fetch EAGER, mapped by `owner`)
- Pets are returned **sorted by name** (case-insensitive ascending) via `PropertyComparator`

### 1.2 Pet Entity

**Source:** `spring-petclinic-customers-service/src/main/java/.../model/Pet.java`

```java
@Entity
@Table(name = "pets")
public class Pet {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name = "name")
    private String name;

    @Column(name = "birth_date")
    @Temporal(TemporalType.DATE)
    private Date birthDate;

    @ManyToOne
    @JoinColumn(name = "type_id")
    private PetType type;

    @ManyToOne
    @JoinColumn(name = "owner_id")
    @JsonIgnore
    private Owner owner;
}
```

**Key details:**
- `birthDate` uses `@Temporal(TemporalType.DATE)` -- date only, no time component
- `owner` is annotated with `@JsonIgnore` to prevent circular serialization
- `type` is eagerly loaded as a nested object

### 1.3 PetType Entity

**Source:** `spring-petclinic-customers-service/src/main/java/.../model/PetType.java`

```java
@Entity
@Table(name = "types")
public class PetType {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name = "name")
    private String name;
}
```

## 2. Vets Service Entities

### 2.1 Vet Entity

**Source:** `spring-petclinic-vets-service/src/main/java/.../model/Vet.java`

```java
@Entity
@Table(name = "vets")
public class Vet {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name = "first_name")
    @NotBlank
    private String firstName;

    @Column(name = "last_name")
    @NotBlank
    private String lastName;

    @ManyToMany(fetch = FetchType.EAGER)
    @JoinTable(name = "vet_specialties",
        joinColumns = @JoinColumn(name = "vet_id"),
        inverseJoinColumns = @JoinColumn(name = "specialty_id"))
    private Set<Specialty> specialties;
}
```

**Relationships:**
- Many-to-Many with Specialty through `vet_specialties` join table
- Specialties are returned **sorted by name** (case-insensitive ascending)

### 2.2 Specialty Entity

**Source:** `spring-petclinic-vets-service/src/main/java/.../model/Specialty.java`

```java
@Entity
@Table(name = "specialties")
public class Specialty {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name = "name")
    private String name;
}
```

## 3. Visits Service Entity

### 3.1 Visit Entity

**Source:** `spring-petclinic-visits-service/src/main/java/.../model/Visit.java`

```java
@Entity
@Table(name = "visits")
public class Visit {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name = "visit_date")
    @Temporal(TemporalType.TIMESTAMP)
    @JsonFormat(pattern = "yyyy-MM-dd")
    private Date date = new Date();

    @Size(max = 8192)
    @Column(name = "description")
    private String description;

    @Column(name = "pet_id")
    private int petId;
}
```

**Key details:**
- `date` defaults to `new Date()` (current timestamp) on object creation
- `date` stored as TIMESTAMP but serialized as `yyyy-MM-dd` via `@JsonFormat`
- `description` has `@Size(max = 8192)` validation -- max 8192 characters
- `petId` is a plain integer (not a JPA relationship) -- this is the cross-service reference

## 4. Repository Interfaces

### 4.1 OwnerRepository
```java
public interface OwnerRepository extends JpaRepository<Owner, Integer> { }
```
Provides standard CRUD: `findAll()`, `findById()`, `save()`, `deleteById()`.

### 4.2 PetRepository
```java
public interface PetRepository extends JpaRepository<Pet, Integer> {
    @Query("SELECT ptype FROM PetType ptype ORDER BY ptype.name")
    List<PetType> findPetTypes();

    @Query("FROM PetType ptype WHERE ptype.id = :typeId")
    Optional<PetType> findPetTypeById(@Param("typeId") int typeId);
}
```
Custom queries for PetType lookup. Standard CRUD for pets.

### 4.3 VetRepository
```java
public interface VetRepository extends JpaRepository<Vet, Integer> { }
```

### 4.4 VisitRepository
```java
public interface VisitRepository extends JpaRepository<Visit, Integer> {
    List<Visit> findByPetId(int petId);
    List<Visit> findByPetIdIn(Collection<Integer> petIds);
}
```
Two custom query methods:
- `findByPetId(int)`: Get all visits for a single pet
- `findByPetIdIn(Collection<Integer>)`: Get visits for multiple pets (batch query, used by API Gateway)

## 5. SQL Schemas

### 5.1 Customers Service Schema (HSQLDB)

```sql
CREATE TABLE types (
  id   INTEGER IDENTITY PRIMARY KEY,
  name VARCHAR(80)
);
CREATE INDEX types_name ON types (name);

CREATE TABLE owners (
  id         INTEGER IDENTITY PRIMARY KEY,
  first_name VARCHAR(30),
  last_name  VARCHAR(30),
  address    VARCHAR(255),
  city       VARCHAR(80),
  telephone  VARCHAR(12)
);
CREATE INDEX owners_last_name ON owners (last_name);

CREATE TABLE pets (
  id         INTEGER IDENTITY PRIMARY KEY,
  name       VARCHAR(30),
  birth_date DATE,
  type_id    INTEGER NOT NULL,
  owner_id   INTEGER NOT NULL
);
ALTER TABLE pets ADD CONSTRAINT fk_pets_owners FOREIGN KEY (owner_id) REFERENCES owners (id);
ALTER TABLE pets ADD CONSTRAINT fk_pets_types FOREIGN KEY (type_id) REFERENCES types (id);
CREATE INDEX pets_name ON pets (name);
```

### 5.2 Vets Service Schema (HSQLDB)

```sql
CREATE TABLE vets (
  id         INTEGER IDENTITY PRIMARY KEY,
  first_name VARCHAR(30),
  last_name  VARCHAR(30)
);
CREATE INDEX vets_last_name ON vets (last_name);

CREATE TABLE specialties (
  id   INTEGER IDENTITY PRIMARY KEY,
  name VARCHAR(80)
);
CREATE INDEX specialties_name ON specialties (name);

CREATE TABLE vet_specialties (
  vet_id       INTEGER NOT NULL,
  specialty_id INTEGER NOT NULL
);
ALTER TABLE vet_specialties ADD CONSTRAINT fk_vet_specialties_vets FOREIGN KEY (vet_id) REFERENCES vets (id);
ALTER TABLE vet_specialties ADD CONSTRAINT fk_vet_specialties_specialties FOREIGN KEY (specialty_id) REFERENCES specialties (id);
```

### 5.3 Visits Service Schema (HSQLDB)

```sql
CREATE TABLE visits (
  id          INTEGER IDENTITY PRIMARY KEY,
  pet_id      INTEGER NOT NULL,
  visit_date  DATE,
  description VARCHAR(8192)
);
CREATE INDEX visits_pet_id ON visits (pet_id);
```

### 5.4 MySQL Variants

The MySQL schemas are equivalent but use:
- `INT(4) UNSIGNED NOT NULL AUTO_INCREMENT` instead of `INTEGER IDENTITY`
- `engine=InnoDB`
- `CREATE DATABASE IF NOT EXISTS petclinic; USE petclinic;` prefix
- The `vet_specialties` table adds `UNIQUE (vet_id, specialty_id)` constraint in MySQL

## 6. Python SQLAlchemy Models

### 6.1 Customers Service Models

```python
# customers_service/models.py
from datetime import date
from sqlalchemy import String, Integer, Date, ForeignKey, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class PetType(Base):
    __tablename__ = "types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String(80))

    # Relationships
    pets: Mapped[list["Pet"]] = relationship(back_populates="type")

    __table_args__ = (Index("types_name", "name"),)


class Owner(Base):
    __tablename__ = "owners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str | None] = mapped_column(String(30))
    last_name: Mapped[str | None] = mapped_column(String(30))
    address: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(80))
    telephone: Mapped[str | None] = mapped_column(String(12))

    # Relationships
    pets: Mapped[list["Pet"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",  # Eager loading equivalent
    )

    __table_args__ = (Index("owners_last_name", "last_name"),)


class Pet(Base):
    __tablename__ = "pets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String(30))
    birth_date: Mapped[date | None] = mapped_column(Date)
    type_id: Mapped[int] = mapped_column(Integer, ForeignKey("types.id"), nullable=False)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("owners.id"), nullable=False)

    # Relationships
    type: Mapped["PetType"] = relationship(back_populates="pets", lazy="selectin")
    owner: Mapped["Owner"] = relationship(back_populates="pets")

    __table_args__ = (Index("pets_name", "name"),)
```

### 6.2 Vets Service Models

```python
# vets_service/models.py
from sqlalchemy import String, Integer, ForeignKey, Index, UniqueConstraint, Table, Column
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


vet_specialties = Table(
    "vet_specialties",
    Base.metadata,
    Column("vet_id", Integer, ForeignKey("vets.id"), nullable=False),
    Column("specialty_id", Integer, ForeignKey("specialties.id"), nullable=False),
    UniqueConstraint("vet_id", "specialty_id"),
)


class Specialty(Base):
    __tablename__ = "specialties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String(80))

    __table_args__ = (Index("specialties_name", "name"),)


class Vet(Base):
    __tablename__ = "vets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str | None] = mapped_column(String(30))
    last_name: Mapped[str | None] = mapped_column(String(30))

    # Relationships
    specialties: Mapped[list["Specialty"]] = relationship(
        secondary=vet_specialties,
        lazy="selectin",  # Eager loading equivalent
    )

    __table_args__ = (Index("vets_last_name", "last_name"),)
```

### 6.3 Visits Service Models

```python
# visits_service/models.py
from datetime import date as date_type
from sqlalchemy import String, Integer, Date, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pet_id: Mapped[int] = mapped_column(Integer, nullable=False)
    visit_date: Mapped[date_type | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(String(8192))

    __table_args__ = (Index("visits_pet_id", "pet_id"),)
```

## 7. Pydantic Schemas

### 7.1 Customers Service Schemas

```python
# customers_service/schemas.py
from datetime import date
from pydantic import BaseModel, Field, field_validator
import re


class PetTypeSchema(BaseModel):
    id: int
    name: str | None = None

    model_config = {"from_attributes": True}


class PetSchema(BaseModel):
    id: int
    name: str | None = None
    birth_date: date | None = Field(None, alias="birthDate")
    type: PetTypeSchema | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class OwnerSchema(BaseModel):
    id: int
    first_name: str = Field(..., alias="firstName")
    last_name: str = Field(..., alias="lastName")
    address: str
    city: str
    telephone: str
    pets: list[PetSchema] = []

    model_config = {"from_attributes": True, "populate_by_name": True}


class OwnerCreateRequest(BaseModel):
    """Used for creating/updating owners."""
    first_name: str = Field(..., min_length=1, alias="firstName")
    last_name: str = Field(..., min_length=1, alias="lastName")
    address: str = Field(..., min_length=1)
    city: str = Field(..., min_length=1)
    telephone: str = Field(..., min_length=1)

    @field_validator("telephone")
    @classmethod
    def telephone_must_be_digits(cls, v: str) -> str:
        if not re.match(r"^\d{1,12}$", v):
            raise ValueError("Telephone must be 1-12 digits")
        return v

    model_config = {"populate_by_name": True}


class PetCreateRequest(BaseModel):
    """Used for creating/updating pets."""
    id: int | None = None
    name: str | None = None
    birth_date: date | None = Field(None, alias="birthDate")
    type_id: int = Field(..., alias="typeId")

    model_config = {"populate_by_name": True}
```

### 7.2 Vets Service Schemas

```python
# vets_service/schemas.py
from pydantic import BaseModel, Field


class SpecialtySchema(BaseModel):
    id: int
    name: str | None = None

    model_config = {"from_attributes": True}


class VetSchema(BaseModel):
    id: int
    first_name: str = Field(..., alias="firstName")
    last_name: str = Field(..., alias="lastName")
    specialties: list[SpecialtySchema] = []

    model_config = {"from_attributes": True, "populate_by_name": True}
```

### 7.3 Visits Service Schemas

```python
# visits_service/schemas.py
from datetime import date
from pydantic import BaseModel, Field


class VisitSchema(BaseModel):
    id: int
    pet_id: int = Field(..., alias="petId")
    date: date = Field(..., alias="visitDate")
    description: str | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class VisitCreateRequest(BaseModel):
    """Used for creating visits."""
    date: date | None = None
    description: str | None = Field(None, max_length=8192)
    pet_id: int = Field(..., alias="petId")

    model_config = {"populate_by_name": True}
```

### 7.4 API Gateway DTOs (Cross-Service Aggregation)

These DTOs are used in the API Gateway's BFF endpoint (`/api/gateway/owners/{ownerId}`):

```python
# api_gateway/schemas.py
from pydantic import BaseModel, Field


class PetTypeDTO(BaseModel):
    name: str


class VisitDetailDTO(BaseModel):
    id: int | None = None
    pet_id: int = Field(..., alias="petId")
    date: str | None = None
    description: str | None = None

    model_config = {"populate_by_name": True}


class PetDetailDTO(BaseModel):
    id: int
    name: str | None = None
    birth_date: str | None = Field(None, alias="birthDate")
    type: PetTypeDTO | None = None
    visits: list[VisitDetailDTO] = []

    model_config = {"populate_by_name": True}


class OwnerDetailDTO(BaseModel):
    id: int
    first_name: str = Field(..., alias="firstName")
    last_name: str = Field(..., alias="lastName")
    address: str | None = None
    city: str | None = None
    telephone: str | None = None
    pets: list[PetDetailDTO] = []

    model_config = {"populate_by_name": True}


class VisitsDTO(BaseModel):
    items: list[VisitDetailDTO] = []
```

## 8. Seed Data

### 8.1 Pet Types

| id | name |
|---|---|
| 1 | cat |
| 2 | dog |
| 3 | lizard |
| 4 | snake |
| 5 | bird |
| 6 | hamster |

### 8.2 Owners

| id | first_name | last_name | address | city | telephone |
|---|---|---|---|---|---|
| 1 | George | Franklin | 110 W. Liberty St. | Madison | 6085551023 |
| 2 | Betty | Davis | 638 Cardinal Ave. | Sun Prairie | 6085551749 |
| 3 | Eduardo | Rodriquez | 2693 Commerce St. | McFarland | 6085558763 |
| 4 | Harold | Davis | 563 Friendly St. | Windsor | 6085553198 |
| 5 | Peter | McTavish | 2387 S. Fair Way | Madison | 6085552765 |
| 6 | Jean | Coleman | 105 N. Lake St. | Monona | 6085552654 |
| 7 | Jeff | Black | 1450 Oak Blvd. | Monona | 6085555387 |
| 8 | Maria | Escobito | 345 Maple St. | Madison | 6085557683 |
| 9 | David | Schroeder | 2749 Blackhawk Trail | Madison | 6085559435 |
| 10 | Carlos | Estaban | 2335 Independence La. | Waunakee | 6085555487 |

### 8.3 Pets

| id | name | birth_date | type_id | owner_id |
|---|---|---|---|---|
| 1 | Leo | 2010-09-07 | 1 (cat) | 1 (George Franklin) |
| 2 | Basil | 2012-08-06 | 6 (hamster) | 2 (Betty Davis) |
| 3 | Rosy | 2011-04-17 | 2 (dog) | 3 (Eduardo Rodriquez) |
| 4 | Jewel | 2010-03-07 | 2 (dog) | 3 (Eduardo Rodriquez) |
| 5 | Iggy | 2010-11-30 | 3 (lizard) | 4 (Harold Davis) |
| 6 | George | 2010-01-20 | 4 (snake) | 5 (Peter McTavish) |
| 7 | Samantha | 2012-09-04 | 1 (cat) | 6 (Jean Coleman) |
| 8 | Max | 2012-09-04 | 1 (cat) | 6 (Jean Coleman) |
| 9 | Lucky | 2011-08-06 | 5 (bird) | 7 (Jeff Black) |
| 10 | Mulligan | 2007-02-24 | 2 (dog) | 8 (Maria Escobito) |
| 11 | Freddy | 2010-03-09 | 5 (bird) | 9 (David Schroeder) |
| 12 | Lucky | 2010-06-24 | 2 (dog) | 10 (Carlos Estaban) |
| 13 | Sly | 2012-06-08 | 1 (cat) | 10 (Carlos Estaban) |

### 8.4 Veterinarians

| id | first_name | last_name |
|---|---|---|
| 1 | James | Carter |
| 2 | Helen | Leary |
| 3 | Linda | Douglas |
| 4 | Rafael | Ortega |
| 5 | Henry | Stevens |
| 6 | Sharon | Jenkins |

### 8.5 Specialties

| id | name |
|---|---|
| 1 | radiology |
| 2 | surgery |
| 3 | dentistry |

### 8.6 Vet-Specialty Associations

| vet_id | specialty_id | Vet | Specialty |
|---|---|---|---|
| 2 | 1 | Helen Leary | radiology |
| 3 | 2 | Linda Douglas | surgery |
| 3 | 3 | Linda Douglas | dentistry |
| 4 | 2 | Rafael Ortega | surgery |
| 5 | 1 | Henry Stevens | radiology |

Note: James Carter (id=1) and Sharon Jenkins (id=6) have **no specialties**.

### 8.7 Visits

| id | pet_id | visit_date | description |
|---|---|---|---|
| 1 | 7 (Samantha) | 2013-01-01 | rabies shot |
| 2 | 8 (Max) | 2013-01-02 | rabies shot |
| 3 | 8 (Max) | 2013-01-03 | neutered |
| 4 | 7 (Samantha) | 2013-01-04 | spayed |

### 8.8 Python Seed Data Script

```python
# seed_data.py
from datetime import date

PET_TYPES = [
    {"id": 1, "name": "cat"},
    {"id": 2, "name": "dog"},
    {"id": 3, "name": "lizard"},
    {"id": 4, "name": "snake"},
    {"id": 5, "name": "bird"},
    {"id": 6, "name": "hamster"},
]

OWNERS = [
    {"id": 1, "first_name": "George", "last_name": "Franklin", "address": "110 W. Liberty St.", "city": "Madison", "telephone": "6085551023"},
    {"id": 2, "first_name": "Betty", "last_name": "Davis", "address": "638 Cardinal Ave.", "city": "Sun Prairie", "telephone": "6085551749"},
    {"id": 3, "first_name": "Eduardo", "last_name": "Rodriquez", "address": "2693 Commerce St.", "city": "McFarland", "telephone": "6085558763"},
    {"id": 4, "first_name": "Harold", "last_name": "Davis", "address": "563 Friendly St.", "city": "Windsor", "telephone": "6085553198"},
    {"id": 5, "first_name": "Peter", "last_name": "McTavish", "address": "2387 S. Fair Way", "city": "Madison", "telephone": "6085552765"},
    {"id": 6, "first_name": "Jean", "last_name": "Coleman", "address": "105 N. Lake St.", "city": "Monona", "telephone": "6085552654"},
    {"id": 7, "first_name": "Jeff", "last_name": "Black", "address": "1450 Oak Blvd.", "city": "Monona", "telephone": "6085555387"},
    {"id": 8, "first_name": "Maria", "last_name": "Escobito", "address": "345 Maple St.", "city": "Madison", "telephone": "6085557683"},
    {"id": 9, "first_name": "David", "last_name": "Schroeder", "address": "2749 Blackhawk Trail", "city": "Madison", "telephone": "6085559435"},
    {"id": 10, "first_name": "Carlos", "last_name": "Estaban", "address": "2335 Independence La.", "city": "Waunakee", "telephone": "6085555487"},
]

PETS = [
    {"id": 1, "name": "Leo", "birth_date": date(2010, 9, 7), "type_id": 1, "owner_id": 1},
    {"id": 2, "name": "Basil", "birth_date": date(2012, 8, 6), "type_id": 6, "owner_id": 2},
    {"id": 3, "name": "Rosy", "birth_date": date(2011, 4, 17), "type_id": 2, "owner_id": 3},
    {"id": 4, "name": "Jewel", "birth_date": date(2010, 3, 7), "type_id": 2, "owner_id": 3},
    {"id": 5, "name": "Iggy", "birth_date": date(2010, 11, 30), "type_id": 3, "owner_id": 4},
    {"id": 6, "name": "George", "birth_date": date(2010, 1, 20), "type_id": 4, "owner_id": 5},
    {"id": 7, "name": "Samantha", "birth_date": date(2012, 9, 4), "type_id": 1, "owner_id": 6},
    {"id": 8, "name": "Max", "birth_date": date(2012, 9, 4), "type_id": 1, "owner_id": 6},
    {"id": 9, "name": "Lucky", "birth_date": date(2011, 8, 6), "type_id": 5, "owner_id": 7},
    {"id": 10, "name": "Mulligan", "birth_date": date(2007, 2, 24), "type_id": 2, "owner_id": 8},
    {"id": 11, "name": "Freddy", "birth_date": date(2010, 3, 9), "type_id": 5, "owner_id": 9},
    {"id": 12, "name": "Lucky", "birth_date": date(2010, 6, 24), "type_id": 2, "owner_id": 10},
    {"id": 13, "name": "Sly", "birth_date": date(2012, 6, 8), "type_id": 1, "owner_id": 10},
]

VETS = [
    {"id": 1, "first_name": "James", "last_name": "Carter"},
    {"id": 2, "first_name": "Helen", "last_name": "Leary"},
    {"id": 3, "first_name": "Linda", "last_name": "Douglas"},
    {"id": 4, "first_name": "Rafael", "last_name": "Ortega"},
    {"id": 5, "first_name": "Henry", "last_name": "Stevens"},
    {"id": 6, "first_name": "Sharon", "last_name": "Jenkins"},
]

SPECIALTIES = [
    {"id": 1, "name": "radiology"},
    {"id": 2, "name": "surgery"},
    {"id": 3, "name": "dentistry"},
]

VET_SPECIALTIES = [
    {"vet_id": 2, "specialty_id": 1},
    {"vet_id": 3, "specialty_id": 2},
    {"vet_id": 3, "specialty_id": 3},
    {"vet_id": 4, "specialty_id": 2},
    {"vet_id": 5, "specialty_id": 1},
]

VISITS = [
    {"id": 1, "pet_id": 7, "visit_date": date(2013, 1, 1), "description": "rabies shot"},
    {"id": 2, "pet_id": 8, "visit_date": date(2013, 1, 2), "description": "rabies shot"},
    {"id": 3, "pet_id": 8, "visit_date": date(2013, 1, 3), "description": "neutered"},
    {"id": 4, "pet_id": 7, "visit_date": date(2013, 1, 4), "description": "spayed"},
]
```

## 9. Database Configuration Notes

### Development (HSQLDB / SQLite)
- HSQLDB runs in-memory (`jdbc:hsqldb:mem:petclinic`)
- Python equivalent: SQLite with `sqlite:///./petclinic.db` or `sqlite+aiosqlite:///./petclinic.db` for async
- Schema auto-created on startup via `Base.metadata.create_all(engine)`

### Production (MySQL / PostgreSQL)
- Each service connects to a separate database (or schema)
- MySQL schemas provided in `src/main/resources/db/mysql/schema.sql`
- Python equivalent: PostgreSQL with `postgresql+asyncpg://user:pass@host:5432/petclinic_customers`

### Alembic Migrations

For the Python rewrite, use Alembic for schema migrations instead of raw SQL:

```python
# alembic/env.py (per service)
from models import Base
target_metadata = Base.metadata
```

Each service should have its own Alembic migration directory since they maintain separate databases.
