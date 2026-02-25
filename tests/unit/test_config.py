"""Tests for shared.config — BaseServiceSettings + YAML loader."""

import textwrap
from pathlib import Path

import pytest

from shared.config import BaseServiceSettings, create_service_settings, load_yaml_config


class TestBaseServiceSettings:
    """Test BaseServiceSettings defaults and env-var overrides."""

    def test_default_values(self) -> None:
        settings = BaseServiceSettings(service_name="test-service")
        assert settings.service_name == "test-service"
        assert settings.service_port == 8080
        assert settings.database_url == "sqlite+aiosqlite:///./petclinic.db"
        assert settings.log_level == "INFO"
        assert settings.config_server_url == "http://localhost:8888"
        assert settings.discovery_server_url == "http://localhost:8761"

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/clinic")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        settings = BaseServiceSettings(service_name="test-service")
        assert settings.database_url == "postgresql+asyncpg://u:p@db:5432/clinic"
        assert settings.log_level == "DEBUG"

    def test_service_url_fields(self) -> None:
        settings = BaseServiceSettings(service_name="test-service")
        assert settings.customers_service_url == "http://localhost:8081"
        assert settings.visits_service_url == "http://localhost:8082"
        assert settings.vets_service_url == "http://localhost:8083"
        assert settings.genai_service_url == "http://localhost:8084"

    def test_observability_defaults(self) -> None:
        settings = BaseServiceSettings(service_name="test-service")
        assert settings.zipkin_endpoint == "http://localhost:9411/api/v2/spans"
        assert settings.prometheus_port == 9091


class TestLoadYamlConfig:
    """Test YAML config loading with merge behavior."""

    def test_loads_application_yml(self, tmp_path: Path) -> None:
        app_yml = tmp_path / "application.yml"
        app_yml.write_text(
            textwrap.dedent("""\
                log_level: WARNING
                service_port: 9000
            """)
        )
        result = load_yaml_config("any-service", config_dir=tmp_path)
        assert result["log_level"] == "WARNING"
        assert result["service_port"] == 9000

    def test_service_overrides_application(self, tmp_path: Path) -> None:
        app_yml = tmp_path / "application.yml"
        app_yml.write_text(
            textwrap.dedent("""\
                log_level: WARNING
                service_port: 9000
            """)
        )
        svc_yml = tmp_path / "customers-service.yml"
        svc_yml.write_text(
            textwrap.dedent("""\
                service_port: 8081
                database_url: "sqlite+aiosqlite:///./customers.db"
            """)
        )
        result = load_yaml_config("customers-service", config_dir=tmp_path)
        assert result["log_level"] == "WARNING"  # from application.yml
        assert result["service_port"] == 8081  # overridden by service
        assert result["database_url"] == "sqlite+aiosqlite:///./customers.db"

    def test_missing_files_returns_empty(self, tmp_path: Path) -> None:
        result = load_yaml_config("nonexistent", config_dir=tmp_path)
        assert result == {}

    def test_empty_yaml_returns_empty(self, tmp_path: Path) -> None:
        app_yml = tmp_path / "application.yml"
        app_yml.write_text("")
        result = load_yaml_config("test-service", config_dir=tmp_path)
        assert result == {}


class TestCreateServiceSettings:
    """Test the factory function that wires YAML + env together."""

    def test_yaml_values_applied(self, tmp_path: Path) -> None:
        svc_yml = tmp_path / "my-service.yml"
        svc_yml.write_text(
            textwrap.dedent("""\
                service_port: 7777
                log_level: DEBUG
            """)
        )
        settings = create_service_settings("my-service", config_dir=tmp_path)
        assert settings.service_port == 7777
        assert settings.log_level == "DEBUG"

    def test_env_takes_precedence_over_yaml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        svc_yml = tmp_path / "my-service.yml"
        svc_yml.write_text("log_level: DEBUG\n")
        monkeypatch.setenv("LOG_LEVEL", "ERROR")
        settings = create_service_settings("my-service", config_dir=tmp_path)
        assert settings.log_level == "ERROR"

    def test_defaults_when_no_yaml(self, tmp_path: Path) -> None:
        settings = create_service_settings("no-config", config_dir=tmp_path)
        assert settings.service_port == 8080
        assert settings.log_level == "INFO"


class TestConfigYamlFiles:
    """Verify the actual config/ YAML files exist and have correct values."""

    CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"

    def test_application_yml_exists(self) -> None:
        assert (self.CONFIG_DIR / "application.yml").is_file()

    def test_application_yml_shared_defaults(self) -> None:
        config = load_yaml_config("nonexistent-service", config_dir=self.CONFIG_DIR)
        assert config["log_level"] == "INFO"
        assert config["zipkin_endpoint"] == "http://localhost:9411/api/v2/spans"

    @pytest.mark.parametrize(
        ("service_name", "expected_port", "has_db"),
        [
            ("customers-service", 8081, True),
            ("vets-service", 8083, True),
            ("visits-service", 8082, True),
            ("api-gateway", 8080, False),
            ("genai-service", 8084, False),
        ],
    )
    def test_service_config_port(
        self, service_name: str, expected_port: int, has_db: bool
    ) -> None:
        settings = create_service_settings(service_name, config_dir=self.CONFIG_DIR)
        assert settings.service_port == expected_port
        if has_db:
            svc_key = service_name.replace("-service", "")
            assert svc_key in settings.database_url

    def test_customers_service_db(self) -> None:
        settings = create_service_settings("customers-service", config_dir=self.CONFIG_DIR)
        assert "customers" in settings.database_url

    def test_vets_service_db(self) -> None:
        settings = create_service_settings("vets-service", config_dir=self.CONFIG_DIR)
        assert "vets" in settings.database_url

    def test_visits_service_db(self) -> None:
        settings = create_service_settings("visits-service", config_dir=self.CONFIG_DIR)
        assert "visits" in settings.database_url

    def test_gateway_service_urls(self) -> None:
        settings = create_service_settings("api-gateway", config_dir=self.CONFIG_DIR)
        assert settings.customers_service_url == "http://localhost:8081"
        assert settings.visits_service_url == "http://localhost:8082"
        assert settings.vets_service_url == "http://localhost:8083"
        assert settings.genai_service_url == "http://localhost:8084"
