"""Tests for Owner SQLAlchemy model — customers_service.models.Owner."""

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

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


class TestOwnerSchema:
    """Verify the Owner model maps to the 'owners' table with correct columns."""

    def test_tablename_is_owners(self) -> None:
        assert Owner.__tablename__ == "owners"

    def test_has_id_column(self) -> None:
        mapper = inspect(Owner)
        assert "id" in mapper.columns

    def test_id_is_primary_key(self) -> None:
        mapper = inspect(Owner)
        pk_cols = [c.name for c in mapper.columns if c.primary_key]
        assert "id" in pk_cols

    def test_has_first_name_column(self) -> None:
        mapper = inspect(Owner)
        assert "first_name" in mapper.columns

    def test_first_name_max_length_30(self) -> None:
        mapper = inspect(Owner)
        col = mapper.columns["first_name"]
        assert col.type.length == 30  # type: ignore[attr-defined]

    def test_first_name_is_nullable(self) -> None:
        mapper = inspect(Owner)
        col = mapper.columns["first_name"]
        assert col.nullable is True

    def test_has_last_name_column(self) -> None:
        mapper = inspect(Owner)
        assert "last_name" in mapper.columns

    def test_last_name_max_length_30(self) -> None:
        mapper = inspect(Owner)
        col = mapper.columns["last_name"]
        assert col.type.length == 30  # type: ignore[attr-defined]

    def test_has_address_column(self) -> None:
        mapper = inspect(Owner)
        assert "address" in mapper.columns

    def test_address_max_length_255(self) -> None:
        mapper = inspect(Owner)
        col = mapper.columns["address"]
        assert col.type.length == 255  # type: ignore[attr-defined]

    def test_has_city_column(self) -> None:
        mapper = inspect(Owner)
        assert "city" in mapper.columns

    def test_city_max_length_80(self) -> None:
        mapper = inspect(Owner)
        col = mapper.columns["city"]
        assert col.type.length == 80  # type: ignore[attr-defined]

    def test_has_telephone_column(self) -> None:
        mapper = inspect(Owner)
        assert "telephone" in mapper.columns

    def test_telephone_max_length_12(self) -> None:
        mapper = inspect(Owner)
        col = mapper.columns["telephone"]
        assert col.type.length == 12  # type: ignore[attr-defined]

    def test_index_on_last_name(self) -> None:
        indexes = Owner.__table__.indexes  # type: ignore[attr-defined]
        ln_indexes = [idx for idx in indexes if "last_name" in [c.name for c in idx.columns]]
        assert len(ln_indexes) >= 1
        idx = ln_indexes[0]
        assert idx.name == "owners_last_name"


class TestOwnerPetsRelationship:
    """Verify the Owner.pets relationship is correctly configured."""

    def test_has_pets_relationship(self) -> None:
        mapper = inspect(Owner)
        assert "pets" in mapper.relationships

    def test_pets_relationship_target_is_pet(self) -> None:
        mapper = inspect(Owner)
        rel = mapper.relationships["pets"]
        assert rel.mapper.class_ is Pet

    def test_pets_relationship_uses_selectin_loading(self) -> None:
        mapper = inspect(Owner)
        rel = mapper.relationships["pets"]
        assert rel.lazy == "selectin"

    def test_pets_relationship_cascade_all_delete_orphan(self) -> None:
        mapper = inspect(Owner)
        rel = mapper.relationships["pets"]
        assert "delete-orphan" in rel.cascade
        assert "save-update" in rel.cascade
        assert "merge" in rel.cascade
        assert "delete" in rel.cascade

    def test_pets_relationship_back_populates_owner(self) -> None:
        mapper = inspect(Owner)
        rel = mapper.relationships["pets"]
        assert rel.back_populates == "owner"


class TestOwnerCRUD:
    """Verify Owner rows can be created, read, and persisted."""

    async def test_insert_and_read(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        async with session_factory() as session:
            owner = Owner(
                first_name="George",
                last_name="Franklin",
                address="110 W. Liberty St.",
                city="Madison",
                telephone="6085551023",
            )
            session.add(owner)
            await session.commit()
            assert owner.id is not None

        async with session_factory() as session:
            loaded = await session.get(Owner, owner.id)
            assert loaded is not None
            assert loaded.first_name == "George"
            assert loaded.last_name == "Franklin"
            assert loaded.address == "110 W. Liberty St."
            assert loaded.city == "Madison"
            assert loaded.telephone == "6085551023"

    async def test_insert_with_null_fields(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        async with session_factory() as session:
            owner = Owner()
            session.add(owner)
            await session.commit()
            assert owner.id is not None

        async with session_factory() as session:
            loaded = await session.get(Owner, owner.id)
            assert loaded is not None
            assert loaded.first_name is None
            assert loaded.last_name is None

    async def test_autoincrement_ids(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        async with session_factory() as session:
            o1 = Owner(first_name="George", last_name="Franklin")
            o2 = Owner(first_name="Betty", last_name="Davis")
            session.add_all([o1, o2])
            await session.commit()
            assert o1.id is not None
            assert o2.id is not None
            assert o2.id > o1.id

    async def test_owner_pets_relationship_loads(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        """Verify that Owner.pets eager-loads associated Pet records."""
        async with session_factory() as session:
            pet_type = PetType(name="cat")
            session.add(pet_type)
            await session.flush()

            owner = Owner(first_name="George", last_name="Franklin")
            session.add(owner)
            await session.flush()

            pet = Pet(name="Leo", owner_id=owner.id, type_id=pet_type.id)
            session.add(pet)
            await session.commit()
            owner_id = owner.id

        async with session_factory() as session:
            loaded = await session.get(Owner, owner_id)
            assert loaded is not None
            assert len(loaded.pets) == 1
            assert loaded.pets[0].name == "Leo"

    async def test_inherits_from_base(self) -> None:
        assert issubclass(Owner, Base)
