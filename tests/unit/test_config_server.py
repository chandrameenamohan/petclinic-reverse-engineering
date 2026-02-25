"""Tests for config server — serves per-service YAML configs via HTTP."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import yaml
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from config_server.main import create_app


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """Create a temp config directory with test YAML files."""
    # application.yml — shared defaults
    app_yml = {
        "log_level": "INFO",
        "zipkin_endpoint": "http://localhost:9411/api/v2/spans",
    }
    (tmp_path / "application.yml").write_text(yaml.dump(app_yml))

    # customers-service.yml — service-specific overrides
    cust_yml = {
        "service_port": 8081,
        "database_url": "sqlite+aiosqlite:///./customers.db",
        "log_level": "DEBUG",
    }
    (tmp_path / "customers-service.yml").write_text(yaml.dump(cust_yml))

    # vets-service.yml
    vets_yml = {
        "service_port": 8083,
    }
    (tmp_path / "vets-service.yml").write_text(yaml.dump(vets_yml))

    return tmp_path


@pytest.fixture
def app(config_dir: Path) -> FastAPI:
    return create_app(config_dir=config_dir)


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestHealthEndpoint:
    async def test_health_returns_up(self, client: AsyncClient) -> None:
        resp = await client.get("/actuator/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "UP"}


class TestInfoEndpoint:
    async def test_info_returns_correct_artifact(self, client: AsyncClient) -> None:
        resp = await client.get("/actuator/info")
        assert resp.status_code == 200
        data = resp.json()
        assert data["build"]["artifact"] == "config-server"
        assert data["build"]["version"] == "1.0.0"
        assert "git" in data


class TestGetConfig:
    async def test_returns_merged_config_for_known_service(self, client: AsyncClient) -> None:
        resp = await client.get("/config/customers-service")
        assert resp.status_code == 200
        data = resp.json()
        # Service-specific value overrides application default
        assert data["log_level"] == "DEBUG"
        # Service-specific value present
        assert data["service_port"] == 8081
        assert data["database_url"] == "sqlite+aiosqlite:///./customers.db"
        # Application-level default present
        assert data["zipkin_endpoint"] == "http://localhost:9411/api/v2/spans"

    async def test_returns_application_defaults_for_unknown_service(
        self, client: AsyncClient
    ) -> None:
        """If no service-specific YAML exists, return only application.yml defaults."""
        resp = await client.get("/config/unknown-service")
        assert resp.status_code == 200
        data = resp.json()
        assert data["log_level"] == "INFO"
        assert data["zipkin_endpoint"] == "http://localhost:9411/api/v2/spans"
        # No service-specific keys
        assert "service_port" not in data

    async def test_returns_service_only_keys(self, client: AsyncClient) -> None:
        resp = await client.get("/config/vets-service")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service_port"] == 8083
        # Inherited from application.yml
        assert data["log_level"] == "INFO"

    async def test_empty_config_dir_returns_empty_dict(self) -> None:
        """Config server with empty config dir returns {} for any service."""
        import tempfile

        with tempfile.TemporaryDirectory() as empty_dir:
            app = create_app(config_dir=Path(empty_dir))
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/config/any-service")
                assert resp.status_code == 200
                assert resp.json() == {}


class TestConfigIsolation:
    """Each app instance uses its own config directory."""

    async def test_separate_apps_have_separate_configs(self, tmp_path: Path) -> None:
        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        (dir1 / "application.yml").write_text(yaml.dump({"source": "dir1"}))

        dir2 = tmp_path / "dir2"
        dir2.mkdir()
        (dir2 / "application.yml").write_text(yaml.dump({"source": "dir2"}))

        app1 = create_app(config_dir=dir1)
        app2 = create_app(config_dir=dir2)

        transport1 = ASGITransport(app=app1)
        async with AsyncClient(transport=transport1, base_url="http://test") as c1:
            resp1 = await c1.get("/config/any")
            assert resp1.json()["source"] == "dir1"

        transport2 = ASGITransport(app=app2)
        async with AsyncClient(transport=transport2, base_url="http://test") as c2:
            resp2 = await c2.get("/config/any")
            assert resp2.json()["source"] == "dir2"
