"""Tests for the shared actuator router — /actuator/health + /actuator/info."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from shared.actuator import create_actuator_router


def _make_app(service_name: str = "test-service") -> FastAPI:
    """Create a minimal FastAPI app with the actuator router."""
    app = FastAPI()
    app.include_router(create_actuator_router(service_name))
    return app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = _make_app("test-service")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestHealthEndpoint:
    """GET /actuator/health returns status UP."""

    async def test_health_returns_200(self, client: AsyncClient) -> None:
        resp = await client.get("/actuator/health")
        assert resp.status_code == 200

    async def test_health_returns_status_up(self, client: AsyncClient) -> None:
        resp = await client.get("/actuator/health")
        assert resp.json() == {"status": "UP"}

    async def test_health_returns_json(self, client: AsyncClient) -> None:
        resp = await client.get("/actuator/health")
        assert "application/json" in resp.headers["content-type"]


class TestInfoEndpoint:
    """GET /actuator/info returns build and git info."""

    async def test_info_returns_200(self, client: AsyncClient) -> None:
        resp = await client.get("/actuator/info")
        assert resp.status_code == 200

    async def test_info_contains_build_section(self, client: AsyncClient) -> None:
        resp = await client.get("/actuator/info")
        data = resp.json()
        assert "build" in data
        assert data["build"]["artifact"] == "test-service"
        assert data["build"]["version"] == "1.0.0"

    async def test_info_contains_git_section(self, client: AsyncClient) -> None:
        resp = await client.get("/actuator/info")
        data = resp.json()
        assert "git" in data
        assert "branch" in data["git"]
        assert "commit" in data["git"]

    async def test_info_git_reads_env_vars(self) -> None:
        """GIT_BRANCH and GIT_COMMIT env vars are reflected in /actuator/info."""
        os.environ["GIT_BRANCH"] = "feature/test"
        os.environ["GIT_COMMIT"] = "abc1234"
        try:
            app = _make_app("my-service")
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/actuator/info")
                data = resp.json()
                assert data["git"]["branch"] == "feature/test"
                assert data["git"]["commit"] == "abc1234"
        finally:
            os.environ.pop("GIT_BRANCH", None)
            os.environ.pop("GIT_COMMIT", None)

    async def test_info_artifact_matches_service_name(self) -> None:
        """Each service gets its own artifact name."""
        app = _make_app("customers-service")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/actuator/info")
            assert resp.json()["build"]["artifact"] == "customers-service"

    async def test_info_defaults_without_env_vars(self, client: AsyncClient) -> None:
        """Without env vars, git defaults to 'main' and 'unknown'."""
        # Ensure env vars are not set
        os.environ.pop("GIT_BRANCH", None)
        os.environ.pop("GIT_COMMIT", None)
        resp = await client.get("/actuator/info")
        data = resp.json()
        assert data["git"]["branch"] == "main"
        assert data["git"]["commit"] == "unknown"
