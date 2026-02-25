"""Integration tests for GET /owners/*/pets/{petId} endpoint."""

from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
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
def app(session_factory: async_sessionmaker[AsyncSession], seeded_db: None) -> FastAPI:
    from fastapi import FastAPI

    from customers_service.routes import get_db, router
    from shared.database import get_db_dependency

    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[get_db] = get_db_dependency(session_factory)
    return application


@pytest.fixture()
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestGetPet:
    """GET /owners/*/pets/{petId} — pet details with owner as string."""

    async def test_get_pet_returns_200(self, client: AsyncClient) -> None:
        resp = await client.get("/owners/1/pets/1")
        assert resp.status_code == 200

    async def test_get_pet_response_has_id(self, client: AsyncClient) -> None:
        resp = await client.get("/owners/1/pets/1")
        data = resp.json()
        assert data["id"] == 1

    async def test_get_pet_response_has_name(self, client: AsyncClient) -> None:
        resp = await client.get("/owners/1/pets/1")
        data = resp.json()
        assert data["name"] == "Leo"

    async def test_get_pet_response_has_owner_as_string(self, client: AsyncClient) -> None:
        """Owner should be 'firstName lastName' concatenated string."""
        resp = await client.get("/owners/1/pets/1")
        data = resp.json()
        assert data["owner"] == "George Franklin"

    async def test_get_pet_response_has_birth_date(self, client: AsyncClient) -> None:
        resp = await client.get("/owners/1/pets/1")
        data = resp.json()
        assert "birthDate" in data

    async def test_get_pet_response_has_type(self, client: AsyncClient) -> None:
        resp = await client.get("/owners/1/pets/1")
        data = resp.json()
        assert data["type"]["id"] == 1
        assert data["type"]["name"] == "cat"

    async def test_get_pet_not_found_returns_404(self, client: AsyncClient) -> None:
        resp = await client.get("/owners/1/pets/9999")
        assert resp.status_code == 404

    async def test_get_pet_wildcard_owner_id(self, client: AsyncClient) -> None:
        """Owner ID in path is irrelevant — pet is looked up by petId only."""
        resp = await client.get("/owners/999/pets/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["owner"] == "George Franklin"
