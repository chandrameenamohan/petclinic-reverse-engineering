"""Integration tests for GET /owners endpoint."""

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


class TestListOwners:
    """GET /owners — list all owners with eager-loaded pets."""

    async def test_returns_200(self, client: AsyncClient) -> None:
        resp = await client.get("/owners")
        assert resp.status_code == 200

    async def test_returns_all_ten_owners(self, client: AsyncClient) -> None:
        resp = await client.get("/owners")
        owners = resp.json()
        assert len(owners) == 10

    async def test_owner_has_camel_case_fields(self, client: AsyncClient) -> None:
        resp = await client.get("/owners")
        owner = resp.json()[0]
        assert "firstName" in owner
        assert "lastName" in owner
        assert "id" in owner
        assert "address" in owner
        assert "city" in owner
        assert "telephone" in owner
        assert "pets" in owner

    async def test_george_franklin_data(self, client: AsyncClient) -> None:
        resp = await client.get("/owners")
        owners = resp.json()
        george = next(o for o in owners if o["id"] == 1)
        assert george["firstName"] == "George"
        assert george["lastName"] == "Franklin"
        assert george["address"] == "110 W. Liberty St."
        assert george["city"] == "Madison"
        assert george["telephone"] == "6085551023"

    async def test_george_has_one_pet_leo(self, client: AsyncClient) -> None:
        resp = await client.get("/owners")
        owners = resp.json()
        george = next(o for o in owners if o["id"] == 1)
        assert len(george["pets"]) == 1
        pet = george["pets"][0]
        assert pet["name"] == "Leo"
        assert pet["birthDate"] == "2010-09-07"
        assert pet["type"]["id"] == 1
        assert pet["type"]["name"] == "cat"

    async def test_jean_coleman_has_two_pets_sorted(self, client: AsyncClient) -> None:
        """Jean Coleman (id=6) has Max and Samantha — should be sorted alphabetically."""
        resp = await client.get("/owners")
        owners = resp.json()
        jean = next(o for o in owners if o["id"] == 6)
        assert len(jean["pets"]) == 2
        pet_names = [p["name"] for p in jean["pets"]]
        assert pet_names == ["Max", "Samantha"]

    async def test_eduardo_has_two_pets_sorted(self, client: AsyncClient) -> None:
        """Eduardo Rodriquez (id=3) has Jewel and Rosy — sorted alphabetically."""
        resp = await client.get("/owners")
        owners = resp.json()
        eduardo = next(o for o in owners if o["id"] == 3)
        pet_names = [p["name"] for p in eduardo["pets"]]
        assert pet_names == ["Jewel", "Rosy"]

    async def test_pets_include_type_object(self, client: AsyncClient) -> None:
        resp = await client.get("/owners")
        owners = resp.json()
        george = next(o for o in owners if o["id"] == 1)
        pet = george["pets"][0]
        assert "type" in pet
        assert "id" in pet["type"]
        assert "name" in pet["type"]

    async def test_empty_db_returns_empty_list(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        tables: None,
    ) -> None:
        """When DB has no owners, returns empty array."""
        from fastapi import FastAPI

        from customers_service.routes import get_db, router
        from shared.database import get_db_dependency

        application = FastAPI()
        application.include_router(router)
        application.dependency_overrides[get_db] = get_db_dependency(session_factory)
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/owners")
            assert resp.status_code == 200
            assert resp.json() == []
