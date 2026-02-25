"""Tests for discovery server — in-memory service registry."""

import pytest
from httpx import ASGITransport, AsyncClient

from discovery_server.main import create_app


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
        assert data["build"]["artifact"] == "discovery-server"
        assert data["build"]["version"] == "1.0.0"
        assert "git" in data


class TestRegisterEndpoint:
    async def test_register_service(self, client):
        resp = await client.post(
            "/register",
            json={"service_name": "customers-service", "host": "localhost", "port": 8081},
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "registered"}

    async def test_register_multiple_instances(self, client):
        await client.post(
            "/register",
            json={"service_name": "customers-service", "host": "host1", "port": 8081},
        )
        await client.post(
            "/register",
            json={"service_name": "customers-service", "host": "host2", "port": 8081},
        )
        resp = await client.get("/services/customers-service")
        assert resp.status_code == 200
        instances = resp.json()
        assert len(instances) == 2

    async def test_register_different_services(self, client):
        await client.post(
            "/register",
            json={"service_name": "customers-service", "host": "localhost", "port": 8081},
        )
        await client.post(
            "/register",
            json={"service_name": "vets-service", "host": "localhost", "port": 8083},
        )
        resp1 = await client.get("/services/customers-service")
        resp2 = await client.get("/services/vets-service")
        assert len(resp1.json()) == 1
        assert len(resp2.json()) == 1

    async def test_register_missing_fields_returns_422(self, client):
        resp = await client.post("/register", json={"service_name": "test"})
        assert resp.status_code == 422

    async def test_register_duplicate_instance_not_duplicated(self, client):
        payload = {"service_name": "customers-service", "host": "localhost", "port": 8081}
        await client.post("/register", json=payload)
        await client.post("/register", json=payload)
        resp = await client.get("/services/customers-service")
        instances = resp.json()
        assert len(instances) == 1


class TestGetServicesEndpoint:
    async def test_get_unknown_service_returns_empty_list(self, client):
        resp = await client.get("/services/unknown-service")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_get_registered_service(self, client):
        await client.post(
            "/register",
            json={"service_name": "vets-service", "host": "localhost", "port": 8083},
        )
        resp = await client.get("/services/vets-service")
        assert resp.status_code == 200
        instances = resp.json()
        assert len(instances) == 1
        assert instances[0]["host"] == "localhost"
        assert instances[0]["port"] == 8083


class TestRegistryIsolation:
    """Each app instance has its own registry (no global state leaks)."""

    async def test_separate_apps_have_separate_registries(self):
        app1 = create_app()
        app2 = create_app()

        transport1 = ASGITransport(app=app1)
        async with AsyncClient(transport=transport1, base_url="http://test") as c1:
            await c1.post(
                "/register",
                json={"service_name": "svc", "host": "h1", "port": 1111},
            )

        transport2 = ASGITransport(app=app2)
        async with AsyncClient(transport=transport2, base_url="http://test") as c2:
            resp = await c2.get("/services/svc")
            assert resp.json() == []
