"""Integration tests for POST /owners/{ownerId}/pets endpoint."""

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


class TestCreatePet:
    """POST /owners/{ownerId}/pets — create a pet for an existing owner."""

    async def test_create_pet_returns_201(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/owners/1/pets",
            json={"name": "Buddy", "birthDate": "2020-05-10", "typeId": 2},
        )
        assert resp.status_code == 201

    async def test_create_pet_response_has_id(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/owners/1/pets",
            json={"name": "Buddy", "birthDate": "2020-05-10", "typeId": 2},
        )
        data = resp.json()
        assert "id" in data
        assert isinstance(data["id"], int)

    async def test_create_pet_response_has_name(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/owners/1/pets",
            json={"name": "Buddy", "birthDate": "2020-05-10", "typeId": 2},
        )
        data = resp.json()
        assert data["name"] == "Buddy"

    async def test_create_pet_response_has_birth_date(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/owners/1/pets",
            json={"name": "Buddy", "birthDate": "2020-05-10", "typeId": 2},
        )
        data = resp.json()
        assert data["birthDate"] == "2020-05-10"

    async def test_create_pet_response_has_type_object(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/owners/1/pets",
            json={"name": "Buddy", "birthDate": "2020-05-10", "typeId": 2},
        )
        data = resp.json()
        assert data["type"]["id"] == 2
        assert data["type"]["name"] == "dog"

    async def test_create_pet_owner_not_found_returns_404(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/owners/9999/pets",
            json={"name": "Ghost", "birthDate": "2020-01-01", "typeId": 1},
        )
        assert resp.status_code == 404

    async def test_create_pet_without_birth_date(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/owners/1/pets",
            json={"name": "NoDate", "typeId": 1},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "NoDate"
        assert data["birthDate"] is None

    async def test_create_pet_persists_in_owner(self, client: AsyncClient) -> None:
        """After creating a pet, it should appear in the owner's pet list."""
        await client.post(
            "/owners/2/pets",
            json={"name": "NewPet", "birthDate": "2021-03-15", "typeId": 3},
        )
        resp = await client.get("/owners/2")
        owner = resp.json()
        pet_names = [p["name"] for p in owner["pets"]]
        assert "NewPet" in pet_names

    async def test_create_pet_id_in_body_ignored(self, client: AsyncClient) -> None:
        """The id field in the request body should be ignored on create."""
        resp = await client.post(
            "/owners/1/pets",
            json={"id": 999, "name": "IgnoreId", "birthDate": "2020-01-01", "typeId": 1},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] != 999
