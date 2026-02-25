"""Tests for visits service seed data — visits_service.seed."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import date

import pytest
from sqlalchemy import select
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


class TestVisitsSeedData:
    """Verify seed_database inserts the 4 canonical visits."""

    async def test_seed_inserts_four_visits(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        from visits_service.seed import seed_database

        await seed_database(session_factory)

        async with session_factory() as session:
            result = await session.execute(select(Visit).order_by(Visit.id))
            visits = result.scalars().all()
            assert len(visits) == 4

    async def test_seed_visit_1_samantha_rabies(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        from visits_service.seed import seed_database

        await seed_database(session_factory)

        async with session_factory() as session:
            visit = await session.get(Visit, 1)
            assert visit is not None
            assert visit.pet_id == 7
            assert visit.visit_date == date(2013, 1, 1)
            assert visit.description == "rabies shot"

    async def test_seed_visit_2_max_rabies(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        from visits_service.seed import seed_database

        await seed_database(session_factory)

        async with session_factory() as session:
            visit = await session.get(Visit, 2)
            assert visit is not None
            assert visit.pet_id == 8
            assert visit.visit_date == date(2013, 1, 2)
            assert visit.description == "rabies shot"

    async def test_seed_visit_3_max_neutered(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        from visits_service.seed import seed_database

        await seed_database(session_factory)

        async with session_factory() as session:
            visit = await session.get(Visit, 3)
            assert visit is not None
            assert visit.pet_id == 8
            assert visit.visit_date == date(2013, 1, 3)
            assert visit.description == "neutered"

    async def test_seed_visit_4_samantha_spayed(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        from visits_service.seed import seed_database

        await seed_database(session_factory)

        async with session_factory() as session:
            visit = await session.get(Visit, 4)
            assert visit is not None
            assert visit.pet_id == 7
            assert visit.visit_date == date(2013, 1, 4)
            assert visit.description == "spayed"

    async def test_seed_is_idempotent(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        from visits_service.seed import seed_database

        await seed_database(session_factory)
        await seed_database(session_factory)

        async with session_factory() as session:
            result = await session.execute(select(Visit))
            visits = result.scalars().all()
            assert len(visits) == 4
