"""Shared configuration infrastructure for all petclinic services.

Provides:
- ``BaseServiceSettings`` — pydantic-settings base with common fields and env-var overrides
- ``load_yaml_config`` — loads application.yml + {service}.yml from a config directory

Resolution order (highest priority wins):
  1. Environment variables
  2. .env file
  3. YAML config files (service-specific overrides application defaults)
  4. Field defaults
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import fields as pydantic_fields
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

# Module-level stash for YAML data; set by create_service_settings() before instantiation.
_yaml_stash: dict[str, object] = {}


def load_yaml_config(
    service_name: str,
    *,
    config_dir: Path | None = None,
) -> dict[str, object]:
    """Load config from ``application.yml`` + ``{service_name}.yml``.

    Service-specific values override application-level defaults.
    Returns an empty dict if no config files are found.
    """
    config_dir = config_dir or Path("config")
    merged: dict[str, object] = {}

    for filename in ("application.yml", f"{service_name}.yml"):
        path = config_dir / filename
        if path.is_file():
            data = yaml.safe_load(path.read_text())
            if isinstance(data, dict):
                merged.update(data)

    return merged


class YamlSettingsSource(PydanticBaseSettingsSource):
    """Custom settings source that reads from YAML config files."""

    def __init__(self, settings_cls: type[BaseSettings], yaml_data: dict[str, object]) -> None:
        super().__init__(settings_cls)
        self._yaml_data = yaml_data

    def get_field_value(self, field: pydantic_fields.FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        val = self._yaml_data.get(field_name)
        return val, field_name, val is not None

    def __call__(self) -> dict[str, Any]:
        return {k: v for k, v in self._yaml_data.items() if v is not None}


class BaseServiceSettings(BaseSettings):
    """Common settings shared by all petclinic services.

    Use ``create_service_settings()`` to build with YAML + env support.
    """

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # --- Identity ---
    service_name: str
    service_port: int = 8080

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./petclinic.db"

    # --- Service URLs ---
    config_server_url: str = "http://localhost:8888"
    discovery_server_url: str = "http://localhost:8761"
    customers_service_url: str = "http://localhost:8081"
    visits_service_url: str = "http://localhost:8082"
    vets_service_url: str = "http://localhost:8083"
    genai_service_url: str = "http://localhost:8084"

    # --- Observability ---
    zipkin_endpoint: str = "http://localhost:9411/api/v2/spans"
    prometheus_port: int = 9091

    # --- Logging ---
    log_level: str = "INFO"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Insert YAML source below dotenv but above defaults."""
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlSettingsSource(settings_cls, _yaml_stash),
            file_secret_settings,
        )


def create_service_settings(
    service_name: str,
    *,
    config_dir: Path | None = None,
) -> BaseServiceSettings:
    """Build settings with YAML config + env vars.

    Priority: env vars > .env file > YAML configs > defaults.
    """
    global _yaml_stash  # noqa: PLW0603
    yaml_data = load_yaml_config(service_name, config_dir=config_dir)
    _yaml_stash = yaml_data
    try:
        return BaseServiceSettings(service_name=service_name)
    finally:
        _yaml_stash = {}
