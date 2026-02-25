"""Tests for customers service seed data — customers_service.seed."""

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import func, select
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


class TestSeedDatabase:
    """Verify seed_database() populates pet types, owners, and pets."""

    async def test_seeds_six_pet_types(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        from customers_service.seed import seed_database

        await seed_database(session_factory)

        async with session_factory() as session:
            result = await session.execute(select(func.count(PetType.id)))
            assert result.scalar() == 6

    async def test_pet_type_names(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        from customers_service.seed import seed_database

        await seed_database(session_factory)

        async with session_factory() as session:
            result = await session.execute(select(PetType).order_by(PetType.id))
            types = result.scalars().all()
            names = [t.name for t in types]
            assert names == ["cat", "dog", "lizard", "snake", "bird", "hamster"]

    async def test_seeds_ten_owners(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        from customers_service.seed import seed_database

        await seed_database(session_factory)

        async with session_factory() as session:
            result = await session.execute(select(func.count(Owner.id)))
            assert result.scalar() == 10

    async def test_owner_data_matches_spec(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        from customers_service.seed import seed_database

        await seed_database(session_factory)

        async with session_factory() as session:
            george = await session.get(Owner, 1)
            assert george is not None
            assert george.first_name == "George"
            assert george.last_name == "Franklin"
            assert george.address == "110 W. Liberty St."
            assert george.city == "Madison"
            assert george.telephone == "6085551023"

            carlos = await session.get(Owner, 10)
            assert carlos is not None
            assert carlos.first_name == "Carlos"
            assert carlos.last_name == "Estaban"
            assert carlos.city == "Waunakee"

    async def test_seeds_thirteen_pets(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        from customers_service.seed import seed_database

        await seed_database(session_factory)

        async with session_factory() as session:
            result = await session.execute(select(func.count(Pet.id)))
            assert result.scalar() == 13

    async def test_pet_data_matches_spec(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        from customers_service.seed import seed_database

        await seed_database(session_factory)

        async with session_factory() as session:
            from datetime import date

            leo = await session.get(Pet, 1)
            assert leo is not None
            assert leo.name == "Leo"
            assert leo.birth_date == date(2010, 9, 7)
            assert leo.type_id == 1  # cat
            assert leo.owner_id == 1  # George Franklin

            sly = await session.get(Pet, 13)
            assert sly is not None
            assert sly.name == "Sly"
            assert sly.birth_date == date(2012, 6, 8)
            assert sly.type_id == 1  # cat
            assert sly.owner_id == 10  # Carlos Estaban

    async def test_pet_owner_relationships(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        """Eduardo Rodriquez (id=3) should have 2 pets: Rosy and Jewel."""
        from customers_service.seed import seed_database

        await seed_database(session_factory)

        async with session_factory() as session:
            eduardo = await session.get(Owner, 3)
            assert eduardo is not None
            pet_names = sorted(p.name for p in eduardo.pets)
            assert pet_names == ["Jewel", "Rosy"]

    async def test_jean_has_two_cats(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        """Jean Coleman (id=6) should have Samantha and Max, both cats."""
        from customers_service.seed import seed_database

        await seed_database(session_factory)

        async with session_factory() as session:
            jean = await session.get(Owner, 6)
            assert jean is not None
            assert len(jean.pets) == 2
            pet_names = sorted(p.name for p in jean.pets)
            assert pet_names == ["Max", "Samantha"]
            for pet in jean.pets:
                assert pet.type_id == 1  # cat


class TestSeedIdempotency:
    """Verify seed_database() is idempotent — running twice yields same data."""

    async def test_double_seed_same_counts(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        from customers_service.seed import seed_database

        await seed_database(session_factory)
        await seed_database(session_factory)

        async with session_factory() as session:
            type_count = (await session.execute(select(func.count(PetType.id)))).scalar()
            owner_count = (await session.execute(select(func.count(Owner.id)))).scalar()
            pet_count = (await session.execute(select(func.count(Pet.id)))).scalar()
            assert type_count == 6
            assert owner_count == 10
            assert pet_count == 13

    async def test_triple_seed_same_counts(
        self, session_factory: async_sessionmaker[AsyncSession], tables: None
    ) -> None:
        from customers_service.seed import seed_database

        await seed_database(session_factory)
        await seed_database(session_factory)
        await seed_database(session_factory)

        async with session_factory() as session:
            type_count = (await session.execute(select(func.count(PetType.id)))).scalar()
            assert type_count == 6
