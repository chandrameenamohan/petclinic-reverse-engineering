"""Integration tests for PUT /owners/{ownerId} — update owner (204, 404)."""

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


class TestUpdateOwner:
    """PUT /owners/{ownerId} — update an existing owner."""

    async def test_returns_204_on_success(self, client: AsyncClient) -> None:
        payload = {
            "firstName": "George",
            "lastName": "Franklin-Updated",
            "address": "110 W. Liberty St.",
            "city": "Madison",
            "telephone": "6085551023",
        }
        resp = await client.put("/owners/1", json=payload)
        assert resp.status_code == 204
        assert resp.content == b""

    async def test_updates_persist_in_db(self, client: AsyncClient) -> None:
        payload = {
            "firstName": "George",
            "lastName": "Franklin-Updated",
            "address": "999 New Address",
            "city": "NewCity",
            "telephone": "1111111111",
        }
        resp = await client.put("/owners/1", json=payload)
        assert resp.status_code == 204

        # Verify via GET
        get_resp = await client.get("/owners/1")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["lastName"] == "Franklin-Updated"
        assert data["address"] == "999 New Address"
        assert data["city"] == "NewCity"
        assert data["telephone"] == "1111111111"

    async def test_returns_404_for_nonexistent_owner(self, client: AsyncClient) -> None:
        payload = {
            "firstName": "Ghost",
            "lastName": "Owner",
            "address": "Nowhere",
            "city": "Void",
            "telephone": "0000000000",
        }
        resp = await client.put("/owners/9999", json=payload)
        assert resp.status_code == 404

    async def test_returns_422_for_invalid_owner_id(self, client: AsyncClient) -> None:
        payload = {
            "firstName": "Test",
            "lastName": "User",
            "address": "123 Test St.",
            "city": "TestCity",
            "telephone": "1234567890",
        }
        resp = await client.put("/owners/0", json=payload)
        assert resp.status_code == 422

    async def test_returns_422_for_missing_first_name(self, client: AsyncClient) -> None:
        payload = {
            "lastName": "User",
            "address": "123 Test St.",
            "city": "TestCity",
            "telephone": "1234567890",
        }
        resp = await client.put("/owners/1", json=payload)
        assert resp.status_code == 422

    async def test_returns_422_for_blank_first_name(self, client: AsyncClient) -> None:
        payload = {
            "firstName": "",
            "lastName": "User",
            "address": "123 Test St.",
            "city": "TestCity",
            "telephone": "1234567890",
        }
        resp = await client.put("/owners/1", json=payload)
        assert resp.status_code == 422

    async def test_returns_422_for_non_digit_telephone(self, client: AsyncClient) -> None:
        payload = {
            "firstName": "Test",
            "lastName": "User",
            "address": "123 Test St.",
            "city": "TestCity",
            "telephone": "abc123",
        }
        resp = await client.put("/owners/1", json=payload)
        assert resp.status_code == 422

    async def test_returns_422_for_telephone_too_long(self, client: AsyncClient) -> None:
        payload = {
            "firstName": "Test",
            "lastName": "User",
            "address": "123 Test St.",
            "city": "TestCity",
            "telephone": "1234567890123",
        }
        resp = await client.put("/owners/1", json=payload)
        assert resp.status_code == 422

    async def test_does_not_affect_pets(self, client: AsyncClient) -> None:
        """Updating owner fields should not affect their pets."""
        # Get current pets
        get_resp = await client.get("/owners/1")
        original_pets = get_resp.json()["pets"]

        payload = {
            "firstName": "George",
            "lastName": "Franklin-Updated",
            "address": "110 W. Liberty St.",
            "city": "Madison",
            "telephone": "6085551023",
        }
        await client.put("/owners/1", json=payload)

        get_resp = await client.get("/owners/1")
        assert get_resp.json()["pets"] == original_pets
