# 03 - REST API Specification

> Comprehensive reference for every REST endpoint in the Spring Petclinic Microservices system.
> Source: actual Java controller/resource classes from the codebase.

---

## Table of Contents

1. [Customers Service (Port 8081)](#1-customers-service-port-8081)
2. [Vets Service (Port 8083)](#2-vets-service-port-8083)
3. [Visits Service (Port 8082)](#3-visits-service-port-8082)
4. [GenAI Service (Port 8084)](#4-genai-service-port-8084)
5. [API Gateway (Port 8080)](#5-api-gateway-port-8080)
6. [Gateway Route Mappings](#6-gateway-route-mappings)
7. [Error Handling](#7-error-handling)
8. [Python FastAPI Equivalents](#8-python-fastapi-equivalents)

---

## 1. Customers Service (Port 8081)

Base path: direct access at `http://localhost:8081`
Via gateway: `http://localhost:8080/api/customer/`

Source files:
- `OwnerResource.java` - `@RequestMapping("/owners")`
- `PetResource.java` - no class-level mapping
- `OwnerRequest.java` - request DTO (Java record)
- `PetRequest.java` - request DTO (Java record)
- `PetDetails.java` - response DTO (Java record)

### 1.1 List All Owners

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/owners` |
| **Controller** | `OwnerResource.findAll()` |
| **Params** | None |
| **Request Body** | None |
| **Response** | `200 OK` - JSON array of Owner objects |
| **Metrics** | `@Timed("petclinic.owner")` |

**Response Body:**
```json
[
  {
    "id": 1,
    "firstName": "George",
    "lastName": "Franklin",
    "address": "110 W. Liberty St.",
    "city": "Madison",
    "telephone": "6085551023",
    "pets": [
      {
        "id": 1,
        "name": "Leo",
        "birthDate": "2010-09-07",
        "type": {
          "id": 1,
          "name": "cat"
        }
      }
    ]
  }
]
```

**Notes:**
- The `pets` field is eagerly fetched (`FetchType.EAGER`) and included in the Owner JSON.
- Pets are sorted alphabetically by name (via `PropertyComparator`).
- The `owner` field on each Pet is annotated with `@JsonIgnore` to prevent circular serialization.

**curl:**
```bash
curl -s http://localhost:8081/owners | jq .
# Via gateway:
curl -s http://localhost:8080/api/customer/owners | jq .
```

---

### 1.2 Get Owner by ID

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/owners/{ownerId}` |
| **Controller** | `OwnerResource.findOwner()` |
| **Path Params** | `ownerId` - integer, `@Min(1)` |
| **Request Body** | None |
| **Response** | `200 OK` - Owner object (wrapped in Optional) |
| **Error** | Returns empty body if not found (Optional behavior) |
| **Metrics** | `@Timed("petclinic.owner")` |

**Response Body:**
```json
{
  "id": 1,
  "firstName": "George",
  "lastName": "Franklin",
  "address": "110 W. Liberty St.",
  "city": "Madison",
  "telephone": "6085551023",
  "pets": [
    {
      "id": 1,
      "name": "Leo",
      "birthDate": "2010-09-07",
      "type": {
        "id": 1,
        "name": "cat"
      }
    }
  ]
}
```

**Important:** The controller returns `Optional<Owner>`. When the owner is not found, Spring returns `200 OK` with a `null` JSON body (not a 404). This is a quirk that the Python reimplementation should replicate or improve upon.

**curl:**
```bash
curl -s http://localhost:8081/owners/1 | jq .
```

---

### 1.3 Create Owner

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/owners` |
| **Controller** | `OwnerResource.createOwner()` |
| **Request Body** | `OwnerRequest` (validated with `@Valid`) |
| **Response** | `201 Created` - the saved Owner object |
| **Metrics** | `@Timed("petclinic.owner")` |

**Request Body (`OwnerRequest` record):**
```json
{
  "firstName": "George",
  "lastName": "Franklin",
  "address": "110 W. Liberty St.",
  "city": "Madison",
  "telephone": "6085551023"
}
```

**Validation Rules:**
| Field | Constraint |
|-------|-----------|
| `firstName` | `@NotBlank` |
| `lastName` | `@NotBlank` |
| `address` | `@NotBlank` |
| `city` | `@NotBlank` |
| `telephone` | `@NotBlank`, `@Digits(fraction=0, integer=12)` - digits only, max 12 chars |

**Response Body:**
```json
{
  "id": 11,
  "firstName": "George",
  "lastName": "Franklin",
  "address": "110 W. Liberty St.",
  "city": "Madison",
  "telephone": "6085551023",
  "pets": []
}
```

**curl:**
```bash
curl -s -X POST http://localhost:8081/owners \
  -H "Content-Type: application/json" \
  -d '{"firstName":"George","lastName":"Franklin","address":"110 W. Liberty St.","city":"Madison","telephone":"6085551023"}' | jq .
```

---

### 1.4 Update Owner

| Field | Value |
|-------|-------|
| **Method** | `PUT` |
| **Path** | `/owners/{ownerId}` |
| **Controller** | `OwnerResource.updateOwner()` |
| **Path Params** | `ownerId` - integer, `@Min(1)` |
| **Request Body** | `OwnerRequest` (validated with `@Valid`) |
| **Response** | `204 No Content` |
| **Error** | `404 Not Found` if owner does not exist |
| **Metrics** | `@Timed("petclinic.owner")` |

**Request Body:** Same as Create Owner.

**Error Case:** Throws `ResourceNotFoundException` which is annotated with `@ResponseStatus(HttpStatus.NOT_FOUND)`, producing:
```
HTTP 404 Not Found
```

**curl:**
```bash
curl -s -X PUT http://localhost:8081/owners/1 \
  -H "Content-Type: application/json" \
  -d '{"firstName":"George","lastName":"Franklin","address":"110 W. Liberty St.","city":"Madison","telephone":"6085551023"}'
# Returns 204 No Content on success
```

---

### 1.5 Get Pet Types

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/petTypes` |
| **Controller** | `PetResource.getPetTypes()` |
| **Params** | None |
| **Response** | `200 OK` - JSON array of PetType objects |
| **Metrics** | `@Timed("petclinic.pet")` |

**Response Body:**
```json
[
  { "id": 1, "name": "cat" },
  { "id": 2, "name": "dog" },
  { "id": 3, "name": "lizard" },
  { "id": 4, "name": "snake" },
  { "id": 5, "name": "bird" },
  { "id": 6, "name": "hamster" }
]
```

**curl:**
```bash
curl -s http://localhost:8081/petTypes | jq .
```

---

### 1.6 Create Pet

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/owners/{ownerId}/pets` |
| **Controller** | `PetResource.processCreationForm()` |
| **Path Params** | `ownerId` - integer, `@Min(1)` |
| **Request Body** | `PetRequest` |
| **Response** | `201 Created` - the saved Pet object |
| **Error** | `404 Not Found` if owner does not exist |
| **Metrics** | `@Timed("petclinic.pet")` |

**Request Body (`PetRequest` record):**
```json
{
  "id": 0,
  "birthDate": "2015-09-07",
  "name": "Leo",
  "typeId": 1
}
```

**Validation Rules:**
| Field | Constraint |
|-------|-----------|
| `name` | `@Size(min=1)` |
| `birthDate` | `@JsonFormat(pattern="yyyy-MM-dd")` |
| `typeId` | integer (references PetType.id) |
| `id` | integer (ignored on create, used on update) |

**Response Body:**
```json
{
  "id": 14,
  "name": "Leo",
  "birthDate": "2015-09-07",
  "type": {
    "id": 1,
    "name": "cat"
  }
}
```

**Note:** The `owner` field is `@JsonIgnore` so it is not serialized in the response.

**curl:**
```bash
curl -s -X POST http://localhost:8081/owners/1/pets \
  -H "Content-Type: application/json" \
  -d '{"id":0,"birthDate":"2015-09-07","name":"Leo","typeId":1}' | jq .
```

---

### 1.7 Update Pet

| Field | Value |
|-------|-------|
| **Method** | `PUT` |
| **Path** | `/owners/*/pets/{petId}` |
| **Controller** | `PetResource.processUpdateForm()` |
| **Path Params** | `petId` in URL is a wildcard `*` for owner; the actual `petId` comes from the request body |
| **Request Body** | `PetRequest` (the `id` field in the body is the actual pet ID used) |
| **Response** | `204 No Content` |
| **Error** | `404 Not Found` if pet does not exist |
| **Metrics** | `@Timed("petclinic.pet")` |

**Important detail:** The path uses `/owners/*/pets/{petId}` but the controller method signature is `processUpdateForm(@RequestBody PetRequest petRequest)` -- the `petId` path variable is NOT extracted. Instead, the pet ID comes from `petRequest.id()`. This is an unusual pattern.

**Request Body:**
```json
{
  "id": 1,
  "birthDate": "2015-09-07",
  "name": "Leo Updated",
  "typeId": 2
}
```

**curl:**
```bash
curl -s -X PUT http://localhost:8081/owners/1/pets/1 \
  -H "Content-Type: application/json" \
  -d '{"id":1,"birthDate":"2015-09-07","name":"Leo Updated","typeId":2}'
# Returns 204 No Content on success
```

---

### 1.8 Get Pet by ID

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/owners/*/pets/{petId}` |
| **Controller** | `PetResource.findPet()` |
| **Path Params** | `petId` - integer |
| **Response** | `200 OK` - PetDetails record |
| **Error** | `404 Not Found` if pet does not exist |
| **Metrics** | `@Timed("petclinic.pet")` |

**Response Body (`PetDetails` record):**
```json
{
  "id": 1,
  "name": "Leo",
  "owner": "George Franklin",
  "birthDate": "2010-09-07",
  "type": {
    "id": 1,
    "name": "cat"
  }
}
```

**Note:** The `owner` field is a concatenation of `firstName + " " + lastName` -- a denormalized string, not the full owner object.

**curl:**
```bash
curl -s http://localhost:8081/owners/1/pets/1 | jq .
```

---

## 2. Vets Service (Port 8083)

Base path: direct access at `http://localhost:8083`
Via gateway: `http://localhost:8080/api/vet/`

Source: `VetResource.java` - `@RequestMapping("/vets")`

### 2.1 List All Vets

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/vets` |
| **Controller** | `VetResource.showResourcesVetList()` |
| **Params** | None |
| **Response** | `200 OK` - JSON array of Vet objects |
| **Caching** | `@Cacheable("vets")` - results are cached |

**Response Body:**
```json
[
  {
    "id": 1,
    "firstName": "James",
    "lastName": "Carter",
    "specialties": []
  },
  {
    "id": 2,
    "firstName": "Helen",
    "lastName": "Leary",
    "specialties": [
      {
        "id": 1,
        "name": "radiology"
      }
    ]
  },
  {
    "id": 3,
    "firstName": "Linda",
    "lastName": "Douglas",
    "specialties": [
      {
        "id": 2,
        "name": "surgery"
      },
      {
        "id": 3,
        "name": "dentistry"
      }
    ]
  }
]
```

**Caching behavior:**
- Uses Spring's `@Cacheable("vets")` annotation.
- The vets list is cached after the first request.
- Cache is never explicitly invalidated (no `@CacheEvict` exists).
- In the gateway, the cache implementation is Caffeine (`com.github.ben-manes.caffeine`).
- The vets service uses the default Spring cache (likely ConcurrentHashMap since no specific cache provider is configured in its pom.xml).

**Notes:**
- Specialties are sorted alphabetically by name.
- Specialties are fetched eagerly (`FetchType.EAGER`) via a `@ManyToMany` join table `vet_specialties`.
- This is the ONLY endpoint on the vets service.

**curl:**
```bash
curl -s http://localhost:8083/vets | jq .
# Via gateway:
curl -s http://localhost:8080/api/vet/vets | jq .
```

---

## 3. Visits Service (Port 8082)

Base path: direct access at `http://localhost:8082`
Via gateway: `http://localhost:8080/api/visit/`

Source: `VisitResource.java` - no class-level `@RequestMapping`

### 3.1 Create Visit

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/owners/*/pets/{petId}/visits` |
| **Controller** | `VisitResource.create()` |
| **Path Params** | `petId` - integer, `@Min(1)` |
| **Request Body** | `Visit` entity (validated with `@Valid`) |
| **Response** | `201 Created` - the saved Visit object |
| **Metrics** | `@Timed("petclinic.visit")` |

**Request Body:**
```json
{
  "date": "2023-01-15",
  "description": "Annual checkup"
}
```

**Validation Rules:**
| Field | Constraint |
|-------|-----------|
| `description` | `@Size(max=8192)` |
| `date` | `@JsonFormat(pattern="yyyy-MM-dd")`, defaults to `new Date()` if not provided |
| `petId` | Set from path variable, NOT from request body |

**Response Body:**
```json
{
  "id": 5,
  "date": "2023-01-15",
  "description": "Annual checkup",
  "petId": 1
}
```

**Note:** The `petId` in the request body is overwritten by the path variable value.

**curl:**
```bash
curl -s -X POST http://localhost:8082/owners/1/pets/1/visits \
  -H "Content-Type: application/json" \
  -d '{"date":"2023-01-15","description":"Annual checkup"}' | jq .
```

---

### 3.2 Get Visits for a Pet

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/owners/*/pets/{petId}/visits` |
| **Controller** | `VisitResource.read()` (single pet) |
| **Path Params** | `petId` - integer, `@Min(1)` |
| **Response** | `200 OK` - JSON array of Visit objects |
| **Metrics** | `@Timed("petclinic.visit")` |

**Response Body:**
```json
[
  {
    "id": 1,
    "date": "2013-01-01",
    "description": "rabies shot",
    "petId": 7
  },
  {
    "id": 2,
    "date": "2013-01-02",
    "description": "rabies shot",
    "petId": 7
  }
]
```

**curl:**
```bash
curl -s http://localhost:8082/owners/1/pets/7/visits | jq .
```

---

### 3.3 Get Visits for Multiple Pets (Batch)

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/pets/visits` |
| **Controller** | `VisitResource.read()` (batch) |
| **Query Params** | `petId` - comma-separated list of integers |
| **Response** | `200 OK` - `Visits` wrapper object |
| **Metrics** | `@Timed("petclinic.visit")` |

**This is a critical endpoint** -- it is used by the API Gateway to aggregate visits for all pets belonging to an owner in a single call.

**Response Body (`Visits` record):**
```json
{
  "items": [
    {
      "id": 1,
      "date": "2013-01-01",
      "description": "rabies shot",
      "petId": 7
    },
    {
      "id": 2,
      "date": "2013-01-02",
      "description": "rabies shot",
      "petId": 8
    }
  ]
}
```

**Note:** The response wraps the list in an `items` field (the `Visits` record has a single field `List<Visit> items`).

**curl:**
```bash
curl -s "http://localhost:8082/pets/visits?petId=7,8" | jq .
# Via gateway:
curl -s "http://localhost:8080/api/visit/pets/visits?petId=7,8" | jq .
```

---

## 4. GenAI Service (Port 8084)

Base path: direct access at `http://localhost:8084`
Via gateway: `http://localhost:8080/api/genai/`

Source: `PetclinicChatClient.java` - `@RequestMapping("/")`

### 4.1 Chat Endpoint

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/chatclient` |
| **Controller** | `PetclinicChatClient.exchange()` |
| **Request Body** | Plain text string (the user's query) |
| **Content-Type** | `text/plain` or `application/json` (raw string) |
| **Response** | `200 OK` - Plain text string (the LLM's response) |
| **Error** | Returns "Chat is currently unavailable. Please try again later." on exception |

**Request Body:**
```
What pets does owner George Franklin have?
```

**Response Body:**
```
George Franklin has one pet named Leo, which is a cat born on September 7, 2010.
```

**Behavior:**
- The chat client uses Spring AI's `ChatClient` with:
  - A system prompt defining the assistant's role as a veterinary clinic helper
  - `MessageChatMemoryAdvisor` for conversation context (up to 10 previous messages)
  - `SimpleLoggerAdvisor` for logging
  - `PetclinicTools` as default tools that the LLM can invoke
- Available LLM tools (function calling):
  - `listOwners()` - fetches all owners from customers-service via REST
  - `addOwnerToPetclinic(OwnerRequest)` - creates owner via customers-service REST
  - `listVets(Vet)` - searches vet vector store via similarity search
  - `addPetToOwner(ownerId, PetRequest)` - creates pet via customers-service REST

**curl:**
```bash
curl -s -X POST http://localhost:8084/chatclient \
  -H "Content-Type: text/plain" \
  -d "What pets does owner George Franklin have?"

# Via gateway:
curl -s -X POST http://localhost:8080/api/genai/chatclient \
  -H "Content-Type: text/plain" \
  -d "List all veterinarians"
```

---

## 5. API Gateway (Port 8080)

Source: `ApiGatewayController.java` - `@RequestMapping("/api/gateway")`

### 5.1 Get Owner Details with Visits (Aggregation Endpoint)

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/api/gateway/owners/{ownerId}` |
| **Controller** | `ApiGatewayController.getOwnerDetails()` |
| **Path Params** | `ownerId` - integer |
| **Response** | `200 OK` - `OwnerDetails` with pets and their visits merged |
| **Circuit Breaker** | `getOwnerDetails` - falls back to empty visits on failure |

**This is the key aggregation endpoint.** It:
1. Calls `customers-service` to get the owner + pets
2. Extracts all pet IDs from the owner
3. Calls `visits-service` to batch-fetch visits for all pets
4. Merges visits into each pet's visits list
5. Returns the combined result

**Response Body (`OwnerDetails` record):**
```json
{
  "id": 1,
  "firstName": "George",
  "lastName": "Franklin",
  "address": "110 W. Liberty St.",
  "city": "Madison",
  "telephone": "6085551023",
  "pets": [
    {
      "id": 1,
      "name": "Leo",
      "birthDate": "2010-09-07",
      "type": {
        "id": 1,
        "name": "cat"
      },
      "visits": [
        {
          "id": 1,
          "petId": 1,
          "date": "2023-01-15",
          "description": "Annual checkup"
        }
      ]
    }
  ]
}
```

**Circuit Breaker Behavior:**
- Uses Resilience4J `ReactiveCircuitBreaker` named `"getOwnerDetails"`.
- If the visits-service call fails, the fallback returns `Visits(List.of())` (empty visits).
- Owner data still returns successfully; only visits are empty on failure.
- Default timeout: 10 seconds (from `TimeLimiterConfig`).

**curl:**
```bash
curl -s http://localhost:8080/api/gateway/owners/1 | jq .
```

---

### 5.2 Fallback Endpoint

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/fallback` |
| **Controller** | `FallbackController.fallback()` |
| **Response** | `503 Service Unavailable` - plain text error message |

**Response Body:**
```
Chat is currently unavailable. Please try again later.
```

This fallback is triggered by the gateway's default circuit breaker filter configured in `application.yml`.

---

## 6. Gateway Route Mappings

The API Gateway uses Spring Cloud Gateway (WebFlux) to proxy requests to backend services. Routes are defined in `application.yml`:

| Route ID | Gateway Path | Target Service | Strip Prefix | Extra Filters |
|----------|-------------|----------------|-------------|---------------|
| `vets-service` | `/api/vet/**` | `lb://vets-service` | 2 | None |
| `visits-service` | `/api/visit/**` | `lb://visits-service` | 2 | None |
| `customers-service` | `/api/customer/**` | `lb://customers-service` | 2 | None |
| `genai-service` | `/api/genai/**` | `lb://genai-service` | 2 | `CircuitBreaker(genaiCircuitBreaker, /fallback)` |

**Path Translation Examples:**

| Client Request | Proxied To |
|---------------|-----------|
| `GET /api/vet/vets` | `GET lb://vets-service/vets` |
| `GET /api/customer/owners` | `GET lb://customers-service/owners` |
| `POST /api/visit/owners/1/pets/1/visits` | `POST lb://visits-service/owners/1/pets/1/visits` |
| `POST /api/genai/chatclient` | `POST lb://genai-service/chatclient` |

**Default Filters (applied to ALL routes):**

1. **CircuitBreaker** (`defaultCircuitBreaker`): Falls back to `forward:/fallback` on failure.
2. **Retry**: 1 retry for `SERVICE_UNAVAILABLE` status on `POST` methods only.

**`lb://` prefix** means the target is resolved via Eureka service discovery with client-side load balancing.

---

## 7. Error Handling

### 7.1 Validation Errors

When `@Valid` validation fails (e.g., missing `firstName` on Owner creation), Spring Boot returns:

```
HTTP 400 Bad Request
```

```json
{
  "timestamp": "2023-01-15T10:30:00.000+00:00",
  "status": 400,
  "error": "Bad Request",
  "path": "/owners"
}
```

### 7.2 Resource Not Found

`ResourceNotFoundException` is annotated with `@ResponseStatus(HttpStatus.NOT_FOUND)`:

```
HTTP 404 Not Found
```

This applies to:
- `PUT /owners/{ownerId}` - when owner does not exist
- `PUT /owners/*/pets/{petId}` - when pet does not exist
- `GET /owners/*/pets/{petId}` - when pet does not exist
- `POST /owners/{ownerId}/pets` - when owner does not exist

### 7.3 Path Variable Validation

`@Min(1)` on path variables (ownerId, petId) causes:

```
HTTP 400 Bad Request (ConstraintViolationException)
```

### 7.4 GenAI Service Errors

The chat endpoint catches all exceptions and returns a `200 OK` with the error string:
```
Chat is currently unavailable. Please try again later.
```

---

## 8. Python FastAPI Equivalents

### 8.1 Owner Endpoints

```python
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/owners", tags=["owners"])


class OwnerRequest(BaseModel):
    first_name: str = Field(..., min_length=1, alias="firstName")
    last_name: str = Field(..., min_length=1, alias="lastName")
    address: str = Field(..., min_length=1)
    city: str = Field(..., min_length=1)
    telephone: str = Field(..., min_length=1, max_length=12, pattern=r"^\d+$")

    model_config = {"populate_by_name": True}


class PetTypeResponse(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class PetResponse(BaseModel):
    id: int
    name: str
    birth_date: str = Field(alias="birthDate")
    type: PetTypeResponse

    model_config = {"from_attributes": True, "populate_by_name": True}


class OwnerResponse(BaseModel):
    id: int
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    address: str
    city: str
    telephone: str
    pets: list[PetResponse] = []

    model_config = {"from_attributes": True, "populate_by_name": True}


@router.get("", response_model=list[OwnerResponse])
async def list_owners(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Owner).options(selectinload(Owner.pets).selectinload(Pet.type))
    )
    return result.scalars().all()


@router.get("/{owner_id}", response_model=OwnerResponse | None)
async def get_owner(owner_id: int = Path(ge=1), db: AsyncSession = Depends(get_db)):
    owner = await db.get(Owner, owner_id, options=[
        selectinload(Owner.pets).selectinload(Pet.type)
    ])
    return owner  # Returns null/None if not found (matches Java Optional behavior)


@router.post("", response_model=OwnerResponse, status_code=status.HTTP_201_CREATED)
async def create_owner(request: OwnerRequest, db: AsyncSession = Depends(get_db)):
    owner = Owner(**request.model_dump())
    db.add(owner)
    await db.commit()
    await db.refresh(owner)
    return owner


@router.put("/{owner_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_owner(
    owner_id: int = Path(ge=1),
    request: OwnerRequest = ...,
    db: AsyncSession = Depends(get_db),
):
    owner = await db.get(Owner, owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail=f"Owner {owner_id} not found")
    for field, value in request.model_dump().items():
        setattr(owner, field, value)
    await db.commit()
```

### 8.2 Pet Endpoints

```python
pet_router = APIRouter(tags=["pets"])


class PetRequest(BaseModel):
    id: int = 0
    birth_date: str = Field(alias="birthDate")
    name: str = Field(min_length=1)
    type_id: int = Field(alias="typeId")

    model_config = {"populate_by_name": True}


class PetDetailsResponse(BaseModel):
    id: int
    name: str
    owner: str  # "firstName lastName" concatenated
    birth_date: str = Field(alias="birthDate")
    type: PetTypeResponse

    model_config = {"from_attributes": True, "populate_by_name": True}


@pet_router.get("/petTypes", response_model=list[PetTypeResponse])
async def get_pet_types(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PetType))
    return result.scalars().all()


@pet_router.post(
    "/owners/{owner_id}/pets",
    response_model=PetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_pet(
    owner_id: int = Path(ge=1),
    request: PetRequest = ...,
    db: AsyncSession = Depends(get_db),
):
    owner = await db.get(Owner, owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail=f"Owner {owner_id} not found")
    pet = Pet(name=request.name, birth_date=request.birth_date, owner_id=owner_id)
    pet_type = await db.get(PetType, request.type_id)
    if pet_type:
        pet.type = pet_type
    db.add(pet)
    await db.commit()
    await db.refresh(pet)
    return pet


@pet_router.put("/owners/{owner_id}/pets/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_pet(request: PetRequest, db: AsyncSession = Depends(get_db)):
    pet = await db.get(Pet, request.id)
    if not pet:
        raise HTTPException(status_code=404, detail=f"Pet {request.id} not found")
    pet.name = request.name
    pet.birth_date = request.birth_date
    pet_type = await db.get(PetType, request.type_id)
    if pet_type:
        pet.type = pet_type
    await db.commit()


@pet_router.get("/owners/{owner_id}/pets/{pet_id}", response_model=PetDetailsResponse)
async def get_pet(pet_id: int, db: AsyncSession = Depends(get_db)):
    pet = await db.get(Pet, pet_id, options=[selectinload(Pet.type), selectinload(Pet.owner)])
    if not pet:
        raise HTTPException(status_code=404, detail=f"Pet {pet_id} not found")
    return PetDetailsResponse(
        id=pet.id,
        name=pet.name,
        owner=f"{pet.owner.first_name} {pet.owner.last_name}",
        birthDate=str(pet.birth_date),
        type=PetTypeResponse(id=pet.type.id, name=pet.type.name),
    )
```

### 8.3 Vet Endpoints

```python
from functools import lru_cache

vet_router = APIRouter(prefix="/vets", tags=["vets"])


class SpecialtyResponse(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class VetResponse(BaseModel):
    id: int
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    specialties: list[SpecialtyResponse] = []

    model_config = {"from_attributes": True, "populate_by_name": True}


# Use cachetools TTLCache or similar for caching equivalent to @Cacheable("vets")
from cachetools import TTLCache, cached

vets_cache = TTLCache(maxsize=1, ttl=3600)


@vet_router.get("", response_model=list[VetResponse])
@cached(cache=vets_cache)
async def list_vets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Vet).options(selectinload(Vet.specialties))
    )
    return result.scalars().all()
```

### 8.4 Visit Endpoints

```python
from datetime import date

visit_router = APIRouter(tags=["visits"])


class VisitRequest(BaseModel):
    date: date | None = None
    description: str = Field(max_length=8192)


class VisitResponse(BaseModel):
    id: int
    date: date
    description: str
    pet_id: int = Field(alias="petId")

    model_config = {"from_attributes": True, "populate_by_name": True}


class VisitsResponse(BaseModel):
    items: list[VisitResponse]


@visit_router.post(
    "/owners/{owner_id}/pets/{pet_id}/visits",
    response_model=VisitResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_visit(
    pet_id: int = Path(ge=1),
    request: VisitRequest = ...,
    db: AsyncSession = Depends(get_db),
):
    visit = Visit(
        date=request.date or date.today(),
        description=request.description,
        pet_id=pet_id,
    )
    db.add(visit)
    await db.commit()
    await db.refresh(visit)
    return visit


@visit_router.get(
    "/owners/{owner_id}/pets/{pet_id}/visits",
    response_model=list[VisitResponse],
)
async def get_visits_for_pet(
    pet_id: int = Path(ge=1),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Visit).where(Visit.pet_id == pet_id))
    return result.scalars().all()


@visit_router.get("/pets/visits", response_model=VisitsResponse)
async def get_visits_for_pets(
    pet_id: list[int] = Query(alias="petId"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Visit).where(Visit.pet_id.in_(pet_id)))
    return VisitsResponse(items=result.scalars().all())
```

### 8.5 Gateway Aggregation Endpoint

```python
import httpx
from circuitbreaker import circuit

gateway_router = APIRouter(prefix="/api/gateway", tags=["gateway"])


class VisitDetails(BaseModel):
    id: int | None = None
    pet_id: int = Field(alias="petId")
    date: str
    description: str

    model_config = {"populate_by_name": True}


class GatewayPetDetails(BaseModel):
    id: int
    name: str
    birth_date: str = Field(alias="birthDate")
    type: PetTypeResponse
    visits: list[VisitDetails] = []

    model_config = {"populate_by_name": True}


class GatewayOwnerDetails(BaseModel):
    id: int
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    address: str
    city: str
    telephone: str
    pets: list[GatewayPetDetails] = []

    model_config = {"populate_by_name": True}


@gateway_router.get("/owners/{owner_id}", response_model=GatewayOwnerDetails)
async def get_owner_details(owner_id: int):
    async with httpx.AsyncClient() as client:
        # Step 1: Get owner from customers-service
        owner_resp = await client.get(f"http://customers-service:8081/owners/{owner_id}")
        owner = GatewayOwnerDetails(**owner_resp.json())

        # Step 2: Batch-fetch visits with circuit breaker fallback
        pet_ids = [pet.id for pet in owner.pets]
        try:
            visits = await _fetch_visits(client, pet_ids)
        except Exception:
            visits = []

        # Step 3: Merge visits into pets
        for pet in owner.pets:
            pet.visits = [v for v in visits if v.pet_id == pet.id]

        return owner


async def _fetch_visits(client: httpx.AsyncClient, pet_ids: list[int]) -> list[VisitDetails]:
    if not pet_ids:
        return []
    ids_param = ",".join(str(pid) for pid in pet_ids)
    resp = await client.get(
        f"http://visits-service:8082/pets/visits",
        params={"petId": ids_param},
    )
    data = resp.json()
    return [VisitDetails(**v) for v in data.get("items", [])]
```

### 8.6 GenAI Chat Endpoint

```python
from openai import AsyncOpenAI

genai_router = APIRouter(tags=["genai"])


@genai_router.post("/chatclient")
async def chat(query: str = Body(..., media_type="text/plain")):
    try:
        # Use LangChain or OpenAI client with tool definitions
        response = await chat_with_tools(query)
        return PlainTextResponse(content=response)
    except Exception:
        return PlainTextResponse(
            content="Chat is currently unavailable. Please try again later."
        )
```

---

## Appendix: Complete Endpoint Summary Table

| Service | Method | Path | Status Codes | Auth |
|---------|--------|------|-------------|------|
| customers | `GET` | `/owners` | 200 | None |
| customers | `GET` | `/owners/{ownerId}` | 200 | None |
| customers | `POST` | `/owners` | 201, 400 | None |
| customers | `PUT` | `/owners/{ownerId}` | 204, 400, 404 | None |
| customers | `GET` | `/petTypes` | 200 | None |
| customers | `POST` | `/owners/{ownerId}/pets` | 201, 400, 404 | None |
| customers | `PUT` | `/owners/*/pets/{petId}` | 204, 404 | None |
| customers | `GET` | `/owners/*/pets/{petId}` | 200, 404 | None |
| vets | `GET` | `/vets` | 200 | None |
| visits | `POST` | `/owners/*/pets/{petId}/visits` | 201, 400 | None |
| visits | `GET` | `/owners/*/pets/{petId}/visits` | 200 | None |
| visits | `GET` | `/pets/visits?petId=1,2,3` | 200 | None |
| genai | `POST` | `/chatclient` | 200 | None |
| gateway | `GET` | `/api/gateway/owners/{ownerId}` | 200 | None |
| gateway | `POST` | `/fallback` | 503 | None |

**Authentication:** None. The entire system has no authentication or authorization. The Python reimplementation should add optional API key or JWT authentication as an enhancement.
