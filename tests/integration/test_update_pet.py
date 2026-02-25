"""Integration tests for PUT /owners/*/pets/{petId} — update pet endpoint."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
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


@pytest.fixture()
async def seeded_db(
    session_factory: async_sessionmaker[AsyncSession], tables: None
) -> None:
    async with session_factory() as session:
        pet_types = [
            PetType(id=1, name="cat"),
            PetType(id=2, name="dog"),
            PetType(id=3, name="lizard"),
        ]
        session.add_all(pet_types)
        await session.flush()

        owner = Owner(
            id=1,
            first_name="George",
            last_name="Franklin",
            address="110 W. Liberty St.",
            city="Madison",
            telephone="6085551023",
        )
        session.add(owner)
        await session.flush()

        pet = Pet(id=1, name="Leo", birth_date=None, type_id=1, owner_id=1)
        session.add(pet)
        await session.commit()


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


class TestUpdatePet:
    """PUT /owners/*/pets/{petId} — update a pet (ID from request body)."""

    async def test_update_pet_returns_204(self, client: AsyncClient) -> None:
        resp = await client.put(
            "/owners/1/pets/1",
            json={"id": 1, "name": "Leo Updated", "birthDate": "2015-09-07", "typeId": 2},
        )
        assert resp.status_code == 204

    async def test_update_pet_changes_name(self, client: AsyncClient) -> None:
        await client.put(
            "/owners/1/pets/1",
            json={"id": 1, "name": "Leo Updated", "birthDate": "2015-09-07", "typeId": 1},
        )
        resp = await client.get("/owners/1")
        owner = resp.json()
        pet_names = [p["name"] for p in owner["pets"]]
        assert "Leo Updated" in pet_names

    async def test_update_pet_changes_type(self, client: AsyncClient) -> None:
        await client.put(
            "/owners/1/pets/1",
            json={"id": 1, "name": "Leo", "birthDate": "2015-09-07", "typeId": 2},
        )
        resp = await client.get("/owners/1")
        owner = resp.json()
        pet = next(p for p in owner["pets"] if p["name"] == "Leo")
        assert pet["type"]["id"] == 2
        assert pet["type"]["name"] == "dog"

    async def test_update_pet_changes_birth_date(self, client: AsyncClient) -> None:
        await client.put(
            "/owners/1/pets/1",
            json={"id": 1, "name": "Leo", "birthDate": "2020-01-15", "typeId": 1},
        )
        resp = await client.get("/owners/1")
        owner = resp.json()
        pet = next(p for p in owner["pets"] if p["name"] == "Leo")
        assert pet["birthDate"] == "2020-01-15"

    async def test_update_pet_not_found_returns_404(self, client: AsyncClient) -> None:
        resp = await client.put(
            "/owners/1/pets/999",
            json={"id": 999, "name": "Ghost", "birthDate": "2020-01-01", "typeId": 1},
        )
        assert resp.status_code == 404

    async def test_update_pet_uses_body_id_not_path(self, client: AsyncClient) -> None:
        """The actual pet ID comes from the request body, not the path parameter."""
        resp = await client.put(
            "/owners/1/pets/999",
            json={"id": 1, "name": "Body ID", "birthDate": "2015-09-07", "typeId": 1},
        )
        # Path says 999 but body says 1 — body wins, pet 1 exists, so 204
        assert resp.status_code == 204

    async def test_update_pet_empty_body_returns_204(self, client: AsyncClient) -> None:
        resp = await client.put(
            "/owners/1/pets/1",
            json={"id": 1, "name": "Leo", "birthDate": "2015-09-07", "typeId": 1},
        )
        assert resp.status_code == 204
        assert resp.content == b""
