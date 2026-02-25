"""Integration tests for vets service main.py — app factory, DB init, seed, health."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def vets_main_app() -> AsyncGenerator[AsyncClient, None]:
    """Create vets service app via create_app() with in-memory SQLite."""
    import os

    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    os.environ["SERVICE_NAME"] = "vets-service"
    os.environ["SERVICE_PORT"] = "8083"

    from vets_service.main import create_app

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

    async def test_health_returns_up(self, vets_main_app: AsyncClient) -> None:
        resp = await vets_main_app.get("/actuator/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "UP"}


class TestInfoEndpoint:
    """GET /actuator/info — returns build and git info."""

    async def test_info_returns_correct_artifact(self, vets_main_app: AsyncClient) -> None:
        resp = await vets_main_app.get("/actuator/info")
        assert resp.status_code == 200
        data = resp.json()
        assert data["build"]["artifact"] == "vets-service"
        assert data["build"]["version"] == "1.0.0"
        assert "git" in data


class TestVetsRouterMounted:
    """Verify vets router is included and functional."""

    async def test_list_vets_via_app(self, vets_main_app: AsyncClient) -> None:
        """GET /vets returns seeded vets through the app."""
        resp = await vets_main_app.get("/vets")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 6

    async def test_vet_camel_case_aliases(self, vets_main_app: AsyncClient) -> None:
        """Vets JSON uses camelCase aliases."""
        resp = await vets_main_app.get("/vets")
        data = resp.json()
        james = next(v for v in data if v["firstName"] == "James")
        assert james["lastName"] == "Carter"


class TestSeedDataLoaded:
    """Verify seed data is loaded on startup."""

    async def test_all_seed_vets_present(self, vets_main_app: AsyncClient) -> None:
        """All 6 seed vets are present after startup."""
        resp = await vets_main_app.get("/vets")
        data = resp.json()
        first_names = {v["firstName"] for v in data}
        assert first_names == {"James", "Helen", "Linda", "Rafael", "Henry", "Sharon"}

    async def test_specialties_seeded(self, vets_main_app: AsyncClient) -> None:
        """Vet-specialty links are seeded correctly."""
        resp = await vets_main_app.get("/vets")
        data = resp.json()
        linda = next(v for v in data if v["firstName"] == "Linda")
        spec_names = [s["name"] for s in linda["specialties"]]
        assert spec_names == ["dentistry", "surgery"]

    async def test_vet_with_no_specialties(self, vets_main_app: AsyncClient) -> None:
        """James Carter has no specialties."""
        resp = await vets_main_app.get("/vets")
        data = resp.json()
        james = next(v for v in data if v["firstName"] == "James")
        assert james["specialties"] == []
