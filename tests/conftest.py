"""Shared test fixtures for petclinic-python tests."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from customers_service.models import Owner, Pet, PetType
from shared.database import Base
from vets_service.models import Specialty, Vet  # noqa: F401  # register vets tables with Base.metadata
from visits_service.models import Visit  # noqa: F401  # register Visit table with Base.metadata


@pytest.fixture
async def async_engine():
    """Create an in-memory async SQLite engine for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def async_session_factory(async_engine):
    """Create an async session factory bound to the test engine."""
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def db_session(async_session_factory):
    """Provide a transactional async session that rolls back after each test."""
    async with async_session_factory() as session:
        yield session


@pytest.fixture
async def seeded_db(async_session_factory):
    """Seed the test database with sample data and return a fresh session."""
    async with async_session_factory() as session:
        # Pet types
        pet_types = [
            PetType(id=1, name="cat"),
            PetType(id=2, name="dog"),
            PetType(id=3, name="lizard"),
            PetType(id=4, name="snake"),
            PetType(id=5, name="bird"),
            PetType(id=6, name="hamster"),
        ]
        session.add_all(pet_types)
        await session.flush()

        # Owners
        owners = [
            Owner(
                id=1, first_name="George", last_name="Franklin",
                address="110 W. Liberty St.", city="Madison", telephone="6085551023",
            ),
            Owner(
                id=2, first_name="Betty", last_name="Davis",
                address="638 Cardinal Ave.", city="Sun Prairie", telephone="6085551749",
            ),
        ]
        session.add_all(owners)
        await session.flush()

        # Pets
        pets = [
            Pet(id=1, name="Leo", birth_date=None, type_id=1, owner_id=1),
            Pet(id=2, name="Basil", birth_date=None, type_id=6, owner_id=2),
        ]
        session.add_all(pets)
        await session.commit()

    # Return a fresh session for the test
    async with async_session_factory() as session:
        yield session


@pytest.fixture
async def customers_app(async_session_factory):
    """Create a FastAPI app with DB dependency overridden for testing."""
    from fastapi import FastAPI

    from customers_service.routes import get_db, router

    app = FastAPI()
    app.include_router(router)

    async def _override_get_db():
        async with async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    return app


@pytest.fixture
async def customers_client(customers_app):
    """Async HTTP client for the customers service."""
    transport = ASGITransport(app=customers_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def seeded_customers_app(async_engine, async_session_factory):
    """Customers app pre-seeded with sample data."""
    from fastapi import FastAPI

    from customers_service.models import Owner, PetType
    from customers_service.routes import get_db, router

    # Seed data
    async with async_session_factory() as session:
        pet_types = [
            PetType(id=1, name="cat"),
            PetType(id=2, name="dog"),
            PetType(id=3, name="lizard"),
            PetType(id=4, name="snake"),
            PetType(id=5, name="bird"),
            PetType(id=6, name="hamster"),
        ]
        session.add_all(pet_types)
        await session.flush()
        owners = [
            Owner(
                id=1, first_name="George", last_name="Franklin",
                address="110 W. Liberty St.", city="Madison", telephone="6085551023",
            ),
            Owner(
                id=2, first_name="Betty", last_name="Davis",
                address="638 Cardinal Ave.", city="Sun Prairie", telephone="6085551749",
            ),
        ]
        session.add_all(owners)
        await session.commit()

    app = FastAPI()
    app.include_router(router)

    async def _override_get_db():
        async with async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    return app


@pytest.fixture
async def seeded_customers_client(seeded_customers_app):
    """Async HTTP client for the seeded customers service."""
    transport = ASGITransport(app=seeded_customers_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
