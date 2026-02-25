"""Tests for Visit SQLAlchemy model — visits_service.models.Visit."""

from collections.abc import AsyncGenerator
from datetime import date

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from shared.database import Base, create_engine, create_session_factory
from visits_service.models import Visit


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


class TestVisitSchema:
    """Verify the Visit model maps to the 'visits' table with correct columns."""

    def test_tablename_is_visits(self) -> None:
        assert Visit.__tablename__ == "visits"

    def test_has_id_column(self) -> None:
        mapper = inspect(Visit)
        assert "id" in mapper.columns

    def test_id_is_primary_key(self) -> None:
        mapper = inspect(Visit)
        pk_cols = [c.name for c in mapper.columns if c.primary_key]
        assert "id" in pk_cols

    def test_id_autoincrement(self) -> None:
        mapper = inspect(Visit)
        col = mapper.columns["id"]
        assert col.autoincrement is not False

    def test_has_pet_id_column(self) -> None:
        mapper = inspect(Visit)
        assert "pet_id" in mapper.columns

    def test_pet_id_is_not_nullable(self) -> None:
        mapper = inspect(Visit)
        col = mapper.columns["pet_id"]
        assert col.nullable is False

    def test_pet_id_has_no_foreign_key(self) -> None:
        """pet_id is a plain int — no FK constraint (cross-service boundary)."""
        mapper = inspect(Visit)
        col = mapper.columns["pet_id"]
        assert len(col.foreign_keys) == 0

    def test_has_visit_date_column(self) -> None:
        mapper = inspect(Visit)
        assert "visit_date" in mapper.columns

    def test_visit_date_is_nullable(self) -> None:
        mapper = inspect(Visit)
        col = mapper.columns["visit_date"]
        assert col.nullable is True

    def test_has_description_column(self) -> None:
        mapper = inspect(Visit)
        assert "description" in mapper.columns

    def test_description_max_length_8192(self) -> None:
        mapper = inspect(Visit)
        col = mapper.columns["description"]
        assert col.type.length == 8192  # type: ignore[attr-defined]

    def test_description_is_nullable(self) -> None:
        mapper = inspect(Visit)
        col = mapper.columns["description"]
        assert col.nullable is True

    def test_index_on_pet_id(self) -> None:
        indexes = Visit.__table__.indexes  # type: ignore[attr-defined]
        pet_id_indexes = [idx for idx in indexes if "pet_id" in [c.name for c in idx.columns]]
        assert len(pet_id_indexes) >= 1
        idx = pet_id_indexes[0]
        assert idx.name == "visits_pet_id"


class TestVisitCRUD:
    """Verify Visit rows can be created, read, and persisted."""

    async def test_insert_and_read(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        async with session_factory() as session:
            visit = Visit(pet_id=7, visit_date=date(2013, 1, 1), description="rabies shot")
            session.add(visit)
            await session.commit()
            visit_id = visit.id

        async with session_factory() as session:
            loaded = await session.get(Visit, visit_id)
            assert loaded is not None
            assert loaded.pet_id == 7
            assert loaded.visit_date == date(2013, 1, 1)
            assert loaded.description == "rabies shot"

    async def test_insert_with_null_date_and_description(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        async with session_factory() as session:
            visit = Visit(pet_id=8, visit_date=None, description=None)
            session.add(visit)
            await session.commit()
            visit_id = visit.id

        async with session_factory() as session:
            loaded = await session.get(Visit, visit_id)
            assert loaded is not None
            assert loaded.pet_id == 8
            assert loaded.visit_date is None
            assert loaded.description is None

    async def test_autoincrement_ids(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        async with session_factory() as session:
            v1 = Visit(pet_id=7, visit_date=date(2013, 1, 1), description="rabies shot")
            v2 = Visit(pet_id=8, visit_date=date(2013, 1, 2), description="neutered")
            session.add_all([v1, v2])
            await session.commit()
            assert v1.id is not None
            assert v2.id is not None
            assert v2.id > v1.id

    async def test_multiple_visits_same_pet(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        async with session_factory() as session:
            v1 = Visit(pet_id=7, visit_date=date(2013, 1, 1), description="rabies shot")
            v2 = Visit(pet_id=7, visit_date=date(2013, 4, 1), description="neutered")
            session.add_all([v1, v2])
            await session.commit()
            assert v1.id != v2.id

    async def test_inherits_from_base(self) -> None:
        assert issubclass(Visit, Base)
