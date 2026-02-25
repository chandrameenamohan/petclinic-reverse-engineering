"""Integration tests for visits service main.py — app factory, DB init, seed, health."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def visits_main_app() -> AsyncGenerator[AsyncClient, None]:
    """Create visits service app via create_app() with in-memory SQLite."""
    import os

    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    os.environ["SERVICE_NAME"] = "visits-service"
    os.environ["SERVICE_PORT"] = "8082"

    from visits_service.main import create_app

    app = create_app()

    # Manually enter the lifespan context (ASGITransport doesn't trigger it)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client

    os.environ.pop("DATABASE_URL", None)
    os.environ.pop("SERVICE_NAME", None)
    os.environ.pop("SERVICE_PORT", None)


class TestHealthEndpoint:
    """GET /actuator/health — returns {"status": "UP"}."""

    async def test_health_returns_up(self, visits_main_app: AsyncClient) -> None:
        resp = await visits_main_app.get("/actuator/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "UP"}


class TestInfoEndpoint:
    """GET /actuator/info — returns build and git info."""

    async def test_info_returns_correct_artifact(self, visits_main_app: AsyncClient) -> None:
        resp = await visits_main_app.get("/actuator/info")
        assert resp.status_code == 200
        data = resp.json()
        assert data["build"]["artifact"] == "visits-service"
        assert data["build"]["version"] == "1.0.0"
        assert "git" in data


class TestVisitsRouterMounted:
    """Verify visits router is included and functional."""

    async def test_create_visit_via_app(self, visits_main_app: AsyncClient) -> None:
        """POST /owners/*/pets/{petId}/visits works through the app."""
        resp = await visits_main_app.post(
            "/owners/1/pets/7/visits",
            json={"date": "2023-01-15", "description": "checkup"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["petId"] == 7
        assert data["description"] == "checkup"

    async def test_batch_query_via_app(self, visits_main_app: AsyncClient) -> None:
        """GET /pets/visits?petId=7,8 works through the app."""
        # Seed visits are inserted on startup (pet_id=7 and pet_id=8)
        resp = await visits_main_app.get("/pets/visits", params={"petId": "7,8"})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        # Seed data has 4 visits: 2 for pet 7, 2 for pet 8
        assert len(data["items"]) == 4

    async def test_get_visits_for_pet_via_app(self, visits_main_app: AsyncClient) -> None:
        """GET /owners/*/pets/{petId}/visits returns seeded visits."""
        resp = await visits_main_app.get("/owners/1/pets/7/visits")
        assert resp.status_code == 200
        data = resp.json()
        # Seed data has 2 visits for pet 7
        assert len(data) == 2
        assert all(v["petId"] == 7 for v in data)


class TestSeedDataLoaded:
    """Verify seed data is loaded on startup."""

    async def test_seed_visits_present(self, visits_main_app: AsyncClient) -> None:
        """All 4 seed visits are present after startup."""
        resp = await visits_main_app.get("/pets/visits", params={"petId": "7,8"})
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 4
        descriptions = {v["description"] for v in items}
        assert "rabies shot" in descriptions
        assert "neutered" in descriptions
        assert "spayed" in descriptions
