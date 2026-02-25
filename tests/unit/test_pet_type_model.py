"""Tests for PetType SQLAlchemy model — customers_service.models.PetType."""

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from customers_service.models import PetType
from shared.database import Base, create_engine, create_session_factory


@pytest.fixture()
def engine() -> AsyncEngine:
    return create_engine("sqlite+aiosqlite:///:memory:")


@pytest.fixture()
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(engine)


@pytest.fixture()
async def tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield  # type: ignore[misc]
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


class TestPetTypeSchema:
    """Verify the PetType model maps to the 'types' table with correct columns."""

    def test_tablename_is_types(self) -> None:
        assert PetType.__tablename__ == "types"

    def test_has_id_column(self) -> None:
        mapper = inspect(PetType)
        assert "id" in mapper.columns

    def test_id_is_primary_key(self) -> None:
        mapper = inspect(PetType)
        pk_cols = [c.name for c in mapper.columns if c.primary_key]
        assert "id" in pk_cols

    def test_has_name_column(self) -> None:
        mapper = inspect(PetType)
        assert "name" in mapper.columns

    def test_name_max_length_80(self) -> None:
        mapper = inspect(PetType)
        col = mapper.columns["name"]
        assert col.type.length == 80

    def test_name_is_nullable(self) -> None:
        mapper = inspect(PetType)
        col = mapper.columns["name"]
        assert col.nullable is True

    def test_index_on_name(self) -> None:
        indexes = PetType.__table__.indexes
        name_indexes = [idx for idx in indexes if "name" in [c.name for c in idx.columns]]
        assert len(name_indexes) >= 1
        idx = name_indexes[0]
        assert idx.name == "types_name"


class TestPetTypeCRUD:
    """Verify PetType rows can be created, read, and persisted."""

    async def test_insert_and_read(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        async with session_factory() as session:
            pt = PetType(name="cat")
            session.add(pt)
            await session.commit()
            assert pt.id is not None

        async with session_factory() as session:
            loaded = await session.get(PetType, pt.id)
            assert loaded is not None
            assert loaded.name == "cat"

    async def test_insert_with_null_name(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        async with session_factory() as session:
            pt = PetType(name=None)
            session.add(pt)
            await session.commit()
            assert pt.id is not None

        async with session_factory() as session:
            loaded = await session.get(PetType, pt.id)
            assert loaded is not None
            assert loaded.name is None

    async def test_autoincrement_ids(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        async with session_factory() as session:
            pt1 = PetType(name="cat")
            pt2 = PetType(name="dog")
            session.add_all([pt1, pt2])
            await session.commit()
            assert pt1.id is not None
            assert pt2.id is not None
            assert pt2.id > pt1.id

    async def test_inherits_from_base(self) -> None:
        assert issubclass(PetType, Base)
