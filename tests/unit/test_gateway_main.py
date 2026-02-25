"""Unit tests for the gateway main.py application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api_gateway.main import create_app


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestGatewayHealthEndpoint:
    async def test_health_returns_200(self, client: AsyncClient) -> None:
        response = await client.get("/actuator/health")
        assert response.status_code == 200

    async def test_health_returns_up(self, client: AsyncClient) -> None:
        response = await client.get("/actuator/health")
        data = response.json()
        assert data == {"status": "UP"}


class TestGatewayInfoEndpoint:
    async def test_info_returns_correct_artifact(self, client: AsyncClient) -> None:
        response = await client.get("/actuator/info")
        assert response.status_code == 200
        data = response.json()
        assert data["build"]["artifact"] == "api-gateway"
        assert data["build"]["version"] == "1.0.0"
        assert "git" in data


class TestGatewayRoutersIncluded:
    """Verify that all expected routers are mounted in the gateway app."""

    async def test_fallback_endpoint_mounted(self, client: AsyncClient) -> None:
        """POST /fallback should be reachable through the main app."""
        response = await client.post("/fallback")
        assert response.status_code == 503
        assert response.text == "Chat is currently unavailable. Please try again later."

    async def test_proxy_route_returns_404_for_unknown_service(self, client: AsyncClient) -> None:
        """Proxy catch-all should be mounted — unknown service returns 404."""
        response = await client.get("/api/unknown/test")
        assert response.status_code == 404

    async def test_bff_route_mounted(self, client: AsyncClient) -> None:
        """BFF route should be mounted — returns 502 when customers-service is down."""
        response = await client.get("/api/gateway/owners/1")
        assert response.status_code == 502


class TestGatewayStaticFiles:
    """Verify static file mount is configured."""

    async def test_static_dir_configured(self, app: FastAPI) -> None:
        """The app should have a static files mount named 'static'."""
        mount_names = [getattr(r, "name", None) for r in app.routes]
        assert "static" in mount_names

    async def test_missing_static_file_returns_404(self, client: AsyncClient) -> None:
        """Request for a non-existent static file should return 404."""
        response = await client.get("/nonexistent-file.txt")
        assert response.status_code == 404


class TestGatewayAppFactory:
    def test_create_app_returns_fastapi(self) -> None:
        app = create_app()
        assert isinstance(app, FastAPI)

    def test_module_level_app_exists(self) -> None:
        from api_gateway.main import app

        assert isinstance(app, FastAPI)

    def test_app_title(self) -> None:
        app = create_app()
        assert app.title == "API Gateway"
