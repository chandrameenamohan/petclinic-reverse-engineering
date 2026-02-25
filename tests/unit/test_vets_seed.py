"""Tests for vets service seed data — vets_service.seed."""

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from shared.database import Base, create_engine, create_session_factory
from vets_service.models import Specialty, Vet, vet_specialties


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


class TestSeedVets:
    """Verify seed_database() populates vets, specialties, and associations."""

    async def test_seeds_six_vets(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        from vets_service.seed import seed_database

        await seed_database(session_factory)

        async with session_factory() as session:
            result = await session.execute(select(func.count(Vet.id)))
            assert result.scalar() == 6

    async def test_seeds_three_specialties(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        from vets_service.seed import seed_database

        await seed_database(session_factory)

        async with session_factory() as session:
            result = await session.execute(select(func.count(Specialty.id)))
            assert result.scalar() == 3

    async def test_specialty_names(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        from vets_service.seed import seed_database

        await seed_database(session_factory)

        async with session_factory() as session:
            result = await session.execute(select(Specialty).order_by(Specialty.id))
            specs = result.scalars().all()
            names = [s.name for s in specs]
            assert names == ["radiology", "surgery", "dentistry"]

    async def test_vet_data_matches_spec(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        from vets_service.seed import seed_database

        await seed_database(session_factory)

        async with session_factory() as session:
            james = await session.get(Vet, 1)
            assert james is not None
            assert james.first_name == "James"
            assert james.last_name == "Carter"

            sharon = await session.get(Vet, 6)
            assert sharon is not None
            assert sharon.first_name == "Sharon"
            assert sharon.last_name == "Jenkins"

    async def test_seeds_five_vet_specialty_links(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        from vets_service.seed import seed_database

        await seed_database(session_factory)

        async with session_factory() as session:
            result = await session.execute(
                select(func.count()).select_from(vet_specialties)
            )
            assert result.scalar() == 5

    async def test_carter_has_no_specialties(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        """James Carter (id=1) has no specialties."""
        from vets_service.seed import seed_database

        await seed_database(session_factory)

        async with session_factory() as session:
            carter = await session.get(Vet, 1)
            assert carter is not None
            assert carter.specialties == []

    async def test_jenkins_has_no_specialties(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        """Sharon Jenkins (id=6) has no specialties."""
        from vets_service.seed import seed_database

        await seed_database(session_factory)

        async with session_factory() as session:
            jenkins = await session.get(Vet, 6)
            assert jenkins is not None
            assert jenkins.specialties == []

    async def test_leary_has_radiology(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        """Helen Leary (id=2) has radiology."""
        from vets_service.seed import seed_database

        await seed_database(session_factory)

        async with session_factory() as session:
            leary = await session.get(Vet, 2)
            assert leary is not None
            spec_names = [s.name for s in leary.specialties]
            assert spec_names == ["radiology"]

    async def test_douglas_has_surgery_and_dentistry(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        """Linda Douglas (id=3) has surgery and dentistry."""
        from vets_service.seed import seed_database

        await seed_database(session_factory)

        async with session_factory() as session:
            douglas = await session.get(Vet, 3)
            assert douglas is not None
            spec_names = sorted(s.name or "" for s in douglas.specialties)
            assert spec_names == ["dentistry", "surgery"]

    async def test_ortega_has_surgery(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        """Rafael Ortega (id=4) has surgery."""
        from vets_service.seed import seed_database

        await seed_database(session_factory)

        async with session_factory() as session:
            ortega = await session.get(Vet, 4)
            assert ortega is not None
            spec_names = [s.name for s in ortega.specialties]
            assert spec_names == ["surgery"]

    async def test_stevens_has_radiology(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        """Henry Stevens (id=5) has radiology."""
        from vets_service.seed import seed_database

        await seed_database(session_factory)

        async with session_factory() as session:
            stevens = await session.get(Vet, 5)
            assert stevens is not None
            spec_names = [s.name for s in stevens.specialties]
            assert spec_names == ["radiology"]


class TestSeedIdempotency:
    """Verify seed_database() is idempotent — running twice yields same data."""

    async def test_double_seed_same_counts(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        from vets_service.seed import seed_database

        await seed_database(session_factory)
        await seed_database(session_factory)

        async with session_factory() as session:
            vet_count = (await session.execute(select(func.count(Vet.id)))).scalar()
            spec_count = (await session.execute(select(func.count(Specialty.id)))).scalar()
            link_count = (
                await session.execute(select(func.count()).select_from(vet_specialties))
            ).scalar()
            assert vet_count == 6
            assert spec_count == 3
            assert link_count == 5
