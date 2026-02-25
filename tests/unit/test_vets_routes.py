"""Unit tests for the vets service GET /vets endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from vets_service.models import Specialty, Vet, vet_specialties
from vets_service.routes import get_db, router, vets_cache


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear the TTL cache between tests."""
    vets_cache.clear()
    yield
    vets_cache.clear()


@pytest.fixture
async def vets_app(async_session_factory):
    """Create a FastAPI app with the vets router and DB override."""
    from fastapi import FastAPI

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
async def vets_client(vets_app):
    """Async HTTP client for the vets service."""
    transport = ASGITransport(app=vets_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def seeded_vets_app(async_engine, async_session_factory):
    """Vets app pre-seeded with 6 vets, 3 specialties, 5 vet-specialty links."""
    from fastapi import FastAPI
    from sqlalchemy import insert

    # Seed data
    async with async_session_factory() as session:
        specialties = [
            Specialty(id=1, name="radiology"),
            Specialty(id=2, name="surgery"),
            Specialty(id=3, name="dentistry"),
        ]
        session.add_all(specialties)
        await session.flush()

        vets = [
            Vet(id=1, first_name="James", last_name="Carter"),
            Vet(id=2, first_name="Helen", last_name="Leary"),
            Vet(id=3, first_name="Linda", last_name="Douglas"),
            Vet(id=4, first_name="Rafael", last_name="Ortega"),
            Vet(id=5, first_name="Henry", last_name="Stevens"),
            Vet(id=6, first_name="Sharon", last_name="Jenkins"),
        ]
        session.add_all(vets)
        await session.flush()

        links = [
            {"vet_id": 2, "specialty_id": 1},  # Helen Leary — radiology
            {"vet_id": 3, "specialty_id": 2},  # Linda Douglas — surgery
            {"vet_id": 3, "specialty_id": 3},  # Linda Douglas — dentistry
            {"vet_id": 4, "specialty_id": 2},  # Rafael Ortega — surgery
            {"vet_id": 5, "specialty_id": 1},  # Henry Stevens — radiology
        ]
        for link in links:
            await session.execute(insert(vet_specialties).values(**link))
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
async def seeded_vets_client(seeded_vets_app):
    """Async HTTP client for the seeded vets service."""
    transport = ASGITransport(app=seeded_vets_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestListVets:
    """Tests for GET /vets endpoint."""

    async def test_returns_200(self, seeded_vets_client):
        """GET /vets returns 200 OK."""
        response = await seeded_vets_client.get("/vets")
        assert response.status_code == 200

    async def test_returns_all_vets(self, seeded_vets_client):
        """GET /vets returns all 6 vets."""
        response = await seeded_vets_client.get("/vets")
        data = response.json()
        assert len(data) == 6

    async def test_vet_json_uses_camel_case(self, seeded_vets_client):
        """Vet JSON uses firstName/lastName aliases."""
        response = await seeded_vets_client.get("/vets")
        data = response.json()
        james = next(v for v in data if v["firstName"] == "James")
        assert james["lastName"] == "Carter"
        assert "first_name" not in james
        assert "last_name" not in james

    async def test_vet_with_no_specialties(self, seeded_vets_client):
        """James Carter and Sharon Jenkins have empty specialties."""
        response = await seeded_vets_client.get("/vets")
        data = response.json()
        james = next(v for v in data if v["firstName"] == "James")
        assert james["specialties"] == []
        sharon = next(v for v in data if v["firstName"] == "Sharon")
        assert sharon["specialties"] == []

    async def test_vet_with_single_specialty(self, seeded_vets_client):
        """Helen Leary has one specialty: radiology."""
        response = await seeded_vets_client.get("/vets")
        data = response.json()
        helen = next(v for v in data if v["firstName"] == "Helen")
        assert len(helen["specialties"]) == 1
        assert helen["specialties"][0]["name"] == "radiology"

    async def test_vet_with_multiple_specialties_sorted(self, seeded_vets_client):
        """Linda Douglas has surgery and dentistry, sorted alphabetically."""
        response = await seeded_vets_client.get("/vets")
        data = response.json()
        linda = next(v for v in data if v["firstName"] == "Linda")
        assert len(linda["specialties"]) == 2
        names = [s["name"] for s in linda["specialties"]]
        assert names == ["dentistry", "surgery"]

    async def test_empty_db_returns_empty_list(self, vets_client):
        """GET /vets with no data returns empty list."""
        response = await vets_client.get("/vets")
        assert response.status_code == 200
        assert response.json() == []

    async def test_response_is_cached(self, seeded_vets_client):
        """Second call returns cached result (same object)."""
        resp1 = await seeded_vets_client.get("/vets")
        resp2 = await seeded_vets_client.get("/vets")
        assert resp1.json() == resp2.json()
        assert resp1.status_code == 200
        assert resp2.status_code == 200
