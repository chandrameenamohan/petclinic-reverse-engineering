"""Tests for admin server — service health dashboard on port 9090."""

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response

from admin_server.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestHealthEndpoint:
    async def test_health_returns_up(self, client):
        resp = await client.get("/actuator/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "UP"}


class TestInfoEndpoint:
    async def test_info_returns_correct_artifact(self, client):
        resp = await client.get("/actuator/info")
        assert resp.status_code == 200
        data = resp.json()
        assert data["build"]["artifact"] == "admin-server"
        assert data["build"]["version"] == "1.0.0"
        assert "git" in data


class TestDashboard:
    """GET /dashboard polls all services' /actuator/health endpoints."""

    @respx.mock
    async def test_all_services_healthy(self, client):
        """When all services respond UP, dashboard shows all UP."""
        for port in (8081, 8082, 8083, 8084, 8080):
            respx.get(f"http://localhost:{port}/actuator/health").mock(
                return_value=Response(200, json={"status": "UP"})
            )

        resp = await client.get("/dashboard")
        assert resp.status_code == 200
        data = resp.json()

        assert data["customers-service"] == {"status": "UP"}
        assert data["visits-service"] == {"status": "UP"}
        assert data["vets-service"] == {"status": "UP"}
        assert data["genai-service"] == {"status": "UP"}
        assert data["api-gateway"] == {"status": "UP"}

    @respx.mock
    async def test_service_down_returns_down(self, client):
        """When a service is unreachable, dashboard shows it as DOWN."""
        # 4 services healthy
        for port in (8081, 8082, 8083, 8080):
            respx.get(f"http://localhost:{port}/actuator/health").mock(
                return_value=Response(200, json={"status": "UP"})
            )
        # genai-service unreachable
        respx.get("http://localhost:8084/actuator/health").mock(
            side_effect=Exception("Connection refused")
        )

        resp = await client.get("/dashboard")
        assert resp.status_code == 200
        data = resp.json()

        assert data["genai-service"] == {"status": "DOWN"}
        assert data["customers-service"] == {"status": "UP"}

    @respx.mock
    async def test_service_returns_non_200(self, client):
        """When a service returns non-200, dashboard shows response as-is."""
        for port in (8081, 8082, 8083, 8084):
            respx.get(f"http://localhost:{port}/actuator/health").mock(
                return_value=Response(200, json={"status": "UP"})
            )
        # api-gateway returns 503
        respx.get("http://localhost:8080/actuator/health").mock(
            return_value=Response(503, json={"status": "DOWN"})
        )

        resp = await client.get("/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["api-gateway"] == {"status": "DOWN"}

    @respx.mock
    async def test_all_services_down(self, client):
        """When all services are unreachable, all show DOWN."""
        for port in (8081, 8082, 8083, 8084, 8080):
            respx.get(f"http://localhost:{port}/actuator/health").mock(
                side_effect=Exception("Connection refused")
            )

        resp = await client.get("/dashboard")
        assert resp.status_code == 200
        data = resp.json()

        for service_status in data.values():
            assert service_status == {"status": "DOWN"}


class TestCustomServices:
    """Admin server can be configured with custom service URLs."""

    @respx.mock
    async def test_custom_services_config(self):
        """create_app accepts custom services dict."""
        custom_services = {
            "my-service": "http://my-host:9999",
        }
        app = create_app(services=custom_services)

        respx.get("http://my-host:9999/actuator/health").mock(
            return_value=Response(200, json={"status": "UP"})
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/dashboard")
            assert resp.status_code == 200
            data = resp.json()
            assert data["my-service"] == {"status": "UP"}
            assert len(data) == 1


class TestAppIsolation:
    """Each app instance has its own service configuration."""

    async def test_separate_apps_have_separate_configs(self):
        app1 = create_app(services={"svc-a": "http://a:1111"})
        app2 = create_app(services={"svc-b": "http://b:2222"})

        assert app1.state.services != app2.state.services
