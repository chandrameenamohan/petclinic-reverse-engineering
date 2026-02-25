"""Tests for Pet SQLAlchemy model — customers_service.models.Pet."""

from collections.abc import AsyncGenerator
from datetime import date

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from customers_service.models import Owner, Pet, PetType
from shared.database import Base, create_engine, create_session_factory


@pytest.fixture()
def engine() -> AsyncEngine:
    return create_engine("sqlite+aiosqlite:///:memory:")


@pytest.fixture()
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(engine)


@pytest.fixture()
async def tables(engine: AsyncEngine) -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


class TestPetSchema:
    """Verify the Pet model maps to the 'pets' table with correct columns."""

    def test_tablename_is_pets(self) -> None:
        assert Pet.__tablename__ == "pets"

    def test_has_id_column(self) -> None:
        mapper = inspect(Pet)
        assert "id" in mapper.columns

    def test_id_is_primary_key(self) -> None:
        mapper = inspect(Pet)
        pk_cols = [c.name for c in mapper.columns if c.primary_key]
        assert "id" in pk_cols

    def test_has_name_column(self) -> None:
        mapper = inspect(Pet)
        assert "name" in mapper.columns

    def test_name_max_length_30(self) -> None:
        mapper = inspect(Pet)
        col = mapper.columns["name"]
        assert col.type.length == 30  # type: ignore[attr-defined]

    def test_name_is_nullable(self) -> None:
        mapper = inspect(Pet)
        col = mapper.columns["name"]
        assert col.nullable is True

    def test_has_birth_date_column(self) -> None:
        mapper = inspect(Pet)
        assert "birth_date" in mapper.columns

    def test_birth_date_is_nullable(self) -> None:
        mapper = inspect(Pet)
        col = mapper.columns["birth_date"]
        assert col.nullable is True

    def test_has_type_id_column(self) -> None:
        mapper = inspect(Pet)
        assert "type_id" in mapper.columns

    def test_type_id_is_not_nullable(self) -> None:
        mapper = inspect(Pet)
        col = mapper.columns["type_id"]
        assert col.nullable is False

    def test_type_id_has_foreign_key_to_types(self) -> None:
        mapper = inspect(Pet)
        col = mapper.columns["type_id"]
        fk_targets = [fk.target_fullname for fk in col.foreign_keys]
        assert "types.id" in fk_targets

    def test_has_owner_id_column(self) -> None:
        mapper = inspect(Pet)
        assert "owner_id" in mapper.columns

    def test_owner_id_is_not_nullable(self) -> None:
        mapper = inspect(Pet)
        col = mapper.columns["owner_id"]
        assert col.nullable is False

    def test_owner_id_has_foreign_key_to_owners(self) -> None:
        mapper = inspect(Pet)
        col = mapper.columns["owner_id"]
        fk_targets = [fk.target_fullname for fk in col.foreign_keys]
        assert "owners.id" in fk_targets

    def test_index_on_name(self) -> None:
        indexes = Pet.__table__.indexes  # type: ignore[attr-defined]
        name_indexes = [idx for idx in indexes if "name" in [c.name for c in idx.columns]]
        assert len(name_indexes) >= 1
        idx = name_indexes[0]
        assert idx.name == "pets_name"


class TestPetRelationships:
    """Verify Pet relationships are correctly configured."""

    def test_has_type_relationship(self) -> None:
        mapper = inspect(Pet)
        assert "type" in mapper.relationships

    def test_type_relationship_target_is_pet_type(self) -> None:
        mapper = inspect(Pet)
        rel = mapper.relationships["type"]
        assert rel.mapper.class_ is PetType

    def test_type_relationship_uses_selectin_loading(self) -> None:
        mapper = inspect(Pet)
        rel = mapper.relationships["type"]
        assert rel.lazy == "selectin"

    def test_type_relationship_back_populates_pets(self) -> None:
        mapper = inspect(Pet)
        rel = mapper.relationships["type"]
        assert rel.back_populates == "pets"

    def test_has_owner_relationship(self) -> None:
        mapper = inspect(Pet)
        assert "owner" in mapper.relationships

    def test_owner_relationship_target_is_owner(self) -> None:
        mapper = inspect(Pet)
        rel = mapper.relationships["owner"]
        assert rel.mapper.class_ is Owner

    def test_owner_relationship_back_populates_pets(self) -> None:
        mapper = inspect(Pet)
        rel = mapper.relationships["owner"]
        assert rel.back_populates == "pets"


class TestPetTypePetsRelationship:
    """Verify PetType.pets bidirectional relationship exists."""

    def test_pet_type_has_pets_relationship(self) -> None:
        mapper = inspect(PetType)
        assert "pets" in mapper.relationships

    def test_pet_type_pets_target_is_pet(self) -> None:
        mapper = inspect(PetType)
        rel = mapper.relationships["pets"]
        assert rel.mapper.class_ is Pet

    def test_pet_type_pets_back_populates_type(self) -> None:
        mapper = inspect(PetType)
        rel = mapper.relationships["pets"]
        assert rel.back_populates == "type"


class TestPetCRUD:
    """Verify Pet rows can be created, read, and persisted."""

    async def test_insert_and_read(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        async with session_factory() as session:
            pet_type = PetType(name="cat")
            session.add(pet_type)
            await session.flush()

            owner = Owner(first_name="George", last_name="Franklin")
            session.add(owner)
            await session.flush()

            pet = Pet(
                name="Leo",
                birth_date=date(2010, 9, 7),
                type_id=pet_type.id,
                owner_id=owner.id,
            )
            session.add(pet)
            await session.commit()
            pet_id = pet.id

        async with session_factory() as session:
            loaded = await session.get(Pet, pet_id)
            assert loaded is not None
            assert loaded.name == "Leo"
            assert loaded.birth_date == date(2010, 9, 7)

    async def test_type_relationship_loads(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        """Pet.type eagerly loads via selectin — PetType is accessible without extra query."""
        async with session_factory() as session:
            pet_type = PetType(name="dog")
            session.add(pet_type)
            await session.flush()

            owner = Owner(first_name="Betty", last_name="Davis")
            session.add(owner)
            await session.flush()

            pet = Pet(name="Rosy", type_id=pet_type.id, owner_id=owner.id)
            session.add(pet)
            await session.commit()
            pet_id = pet.id

        async with session_factory() as session:
            loaded = await session.get(Pet, pet_id)
            assert loaded is not None
            assert loaded.type is not None
            assert loaded.type.name == "dog"

    async def test_owner_relationship_loads(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        """Pet.owner uses default lazy loading; test with explicit selectinload."""
        async with session_factory() as session:
            pet_type = PetType(name="cat")
            session.add(pet_type)
            await session.flush()

            owner = Owner(first_name="George", last_name="Franklin")
            session.add(owner)
            await session.flush()

            pet = Pet(name="Leo", type_id=pet_type.id, owner_id=owner.id)
            session.add(pet)
            await session.commit()
            pet_id = pet.id

        async with session_factory() as session:
            loaded = await session.get(
                Pet, pet_id, options=[selectinload(Pet.owner)]
            )
            assert loaded is not None
            assert loaded.owner is not None
            assert loaded.owner.first_name == "George"

    async def test_pet_type_pets_bidirectional(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        """PetType.pets returns associated pets (bidirectional relationship)."""
        async with session_factory() as session:
            pet_type = PetType(name="cat")
            session.add(pet_type)
            await session.flush()

            owner = Owner(first_name="Jean", last_name="Coleman")
            session.add(owner)
            await session.flush()

            p1 = Pet(name="Samantha", type_id=pet_type.id, owner_id=owner.id)
            p2 = Pet(name="Max", type_id=pet_type.id, owner_id=owner.id)
            session.add_all([p1, p2])
            await session.commit()
            pt_id = pet_type.id

        async with session_factory() as session:
            loaded_pt = await session.get(
                PetType, pt_id, options=[selectinload(PetType.pets)]
            )
            assert loaded_pt is not None
            assert len(loaded_pt.pets) == 2
            names = sorted(p.name for p in loaded_pt.pets if p.name)
            assert names == ["Max", "Samantha"]

    async def test_insert_with_null_name_and_birth_date(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        async with session_factory() as session:
            pet_type = PetType(name="snake")
            session.add(pet_type)
            await session.flush()

            owner = Owner(first_name="Peter", last_name="McTavish")
            session.add(owner)
            await session.flush()

            pet = Pet(name=None, birth_date=None, type_id=pet_type.id, owner_id=owner.id)
            session.add(pet)
            await session.commit()
            pet_id = pet.id

        async with session_factory() as session:
            loaded = await session.get(Pet, pet_id)
            assert loaded is not None
            assert loaded.name is None
            assert loaded.birth_date is None

    async def test_autoincrement_ids(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        async with session_factory() as session:
            pet_type = PetType(name="cat")
            session.add(pet_type)
            await session.flush()

            owner = Owner(first_name="George", last_name="Franklin")
            session.add(owner)
            await session.flush()

            p1 = Pet(name="Leo", type_id=pet_type.id, owner_id=owner.id)
            p2 = Pet(name="Basil", type_id=pet_type.id, owner_id=owner.id)
            session.add_all([p1, p2])
            await session.commit()
            assert p1.id is not None
            assert p2.id is not None
            assert p2.id > p1.id

    async def test_inherits_from_base(self) -> None:
        assert issubclass(Pet, Base)
