"""Integration tests for customers service main.py — app factory, DB init, seed, health."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def customers_main_app() -> AsyncGenerator[AsyncClient, None]:
    """Create customers service app via create_app() with in-memory SQLite."""
    import os

    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    os.environ["SERVICE_NAME"] = "customers-service"
    os.environ["SERVICE_PORT"] = "8081"

    from customers_service.main import create_app

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

    async def test_health_returns_up(self, customers_main_app: AsyncClient) -> None:
        resp = await customers_main_app.get("/actuator/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "UP"}


class TestInfoEndpoint:
    """GET /actuator/info — returns build and git info."""

    async def test_info_returns_correct_artifact(self, customers_main_app: AsyncClient) -> None:
        resp = await customers_main_app.get("/actuator/info")
        assert resp.status_code == 200
        data = resp.json()
        assert data["build"]["artifact"] == "customers-service"
        assert data["build"]["version"] == "1.0.0"
        assert "git" in data


class TestCustomersRouterMounted:
    """Verify customers router is included and functional."""

    async def test_list_owners_via_app(self, customers_main_app: AsyncClient) -> None:
        """GET /owners returns seeded owners through the app."""
        resp = await customers_main_app.get("/owners")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 10

    async def test_owner_camel_case_aliases(self, customers_main_app: AsyncClient) -> None:
        """Owners JSON uses camelCase aliases."""
        resp = await customers_main_app.get("/owners")
        data = resp.json()
        george = next(o for o in data if o["firstName"] == "George")
        assert george["lastName"] == "Franklin"

    async def test_get_pet_types_via_app(self, customers_main_app: AsyncClient) -> None:
        """GET /petTypes returns seeded pet types through the app."""
        resp = await customers_main_app.get("/petTypes")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 6


class TestSeedDataLoaded:
    """Verify seed data is loaded on startup."""

    async def test_all_seed_owners_present(self, customers_main_app: AsyncClient) -> None:
        """All 10 seed owners are present after startup."""
        resp = await customers_main_app.get("/owners")
        data = resp.json()
        first_names = {o["firstName"] for o in data}
        assert first_names == {
            "George", "Betty", "Eduardo", "Harold", "Peter",
            "Jean", "Jeff", "Maria", "David", "Carlos",
        }

    async def test_pets_seeded_with_owners(self, customers_main_app: AsyncClient) -> None:
        """George Franklin's pet Leo is seeded."""
        resp = await customers_main_app.get("/owners/1")
        data = resp.json()
        assert data["firstName"] == "George"
        pet_names = [p["name"] for p in data["pets"]]
        assert "Leo" in pet_names

    async def test_pet_types_seeded(self, customers_main_app: AsyncClient) -> None:
        """All 6 pet types are seeded and sorted alphabetically."""
        resp = await customers_main_app.get("/petTypes")
        data = resp.json()
        names = [t["name"] for t in data]
        assert names == ["bird", "cat", "dog", "hamster", "lizard", "snake"]
