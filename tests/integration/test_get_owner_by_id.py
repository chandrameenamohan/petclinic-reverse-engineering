"""Integration tests for GET /owners/{ownerId} — return owner or null."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

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


@pytest.fixture()
async def seeded_db(
    session_factory: async_sessionmaker[AsyncSession], tables: None
) -> None:
    from customers_service.seed import seed_database

    await seed_database(session_factory)


@pytest.fixture()
def app(session_factory: async_sessionmaker[AsyncSession], seeded_db: None):  # noqa: ANN201
    from fastapi import FastAPI

    from customers_service.routes import get_db, router
    from shared.database import get_db_dependency

    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[get_db] = get_db_dependency(session_factory)
    return application


@pytest.fixture()
async def client(app) -> AsyncGenerator[AsyncClient, None]:  # noqa: ANN001
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestGetOwnerById:
    """GET /owners/{ownerId} — return owner with pets or null if not found."""

    async def test_returns_200_with_existing_owner(self, client: AsyncClient) -> None:
        resp = await client.get("/owners/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data is not None
        assert data["id"] == 1
        assert data["firstName"] == "George"
        assert data["lastName"] == "Franklin"

    async def test_returns_full_owner_fields(self, client: AsyncClient) -> None:
        resp = await client.get("/owners/1")
        data = resp.json()
        assert data["address"] == "110 W. Liberty St."
        assert data["city"] == "Madison"
        assert data["telephone"] == "6085551023"

    async def test_owner_includes_pets_with_type(self, client: AsyncClient) -> None:
        resp = await client.get("/owners/1")
        data = resp.json()
        assert "pets" in data
        assert len(data["pets"]) == 1
        pet = data["pets"][0]
        assert pet["name"] == "Leo"
        assert pet["birthDate"] == "2010-09-07"
        assert pet["type"]["id"] == 1
        assert pet["type"]["name"] == "cat"

    async def test_pets_sorted_alphabetically(self, client: AsyncClient) -> None:
        """Jean Coleman (id=6) has Max and Samantha — sorted alphabetically."""
        resp = await client.get("/owners/6")
        data = resp.json()
        pet_names = [p["name"] for p in data["pets"]]
        assert pet_names == ["Max", "Samantha"]

    async def test_returns_null_for_nonexistent_owner(self, client: AsyncClient) -> None:
        """Non-existent owner returns 200 with null body (Java Optional behavior)."""
        resp = await client.get("/owners/9999")
        assert resp.status_code == 200
        assert resp.json() is None

    async def test_returns_422_for_invalid_owner_id(self, client: AsyncClient) -> None:
        """ownerId must be >= 1."""
        resp = await client.get("/owners/0")
        assert resp.status_code == 422

    async def test_returns_422_for_negative_owner_id(self, client: AsyncClient) -> None:
        resp = await client.get("/owners/-1")
        assert resp.status_code == 422

    async def test_camel_case_field_names(self, client: AsyncClient) -> None:
        resp = await client.get("/owners/2")
        data = resp.json()
        assert "firstName" in data
        assert "lastName" in data
        assert "first_name" not in data
        assert "last_name" not in data
