"""Config Server — serves per-service YAML configuration via HTTP.

Merges ``application.yml`` (shared defaults) with ``{service_name}.yml``
(service-specific overrides) and returns the result as JSON.
Port 8888.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from fastapi import FastAPI
from loguru import logger

from shared.actuator import create_actuator_router


def _load_merged_config(service_name: str, config_dir: Path) -> dict[str, object]:
    """Load application.yml + {service_name}.yml, merging with service overrides."""
    merged: dict[str, object] = {}

    for filename in ("application.yml", f"{service_name}.yml"):
        path = config_dir / filename
        if path.is_file():
            data = yaml.safe_load(path.read_text())
            if isinstance(data, dict):
                merged.update(data)

    return merged


def create_app(*, config_dir: Path | None = None) -> FastAPI:
    """Create and configure the Config Server application."""
    resolved_dir = config_dir or Path("config")

    app = FastAPI(title="Config Server")

    # Store config_dir on app.state so the route can access it
    app.state.config_dir = resolved_dir

    @app.get("/config/{service_name}")
    async def get_config(service_name: str) -> dict[str, object]:
        return _load_merged_config(service_name, app.state.config_dir)

    app.include_router(create_actuator_router("config-server"))

    logger.info("Config server configured (config_dir={})", resolved_dir)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("config_server.main:app", host="0.0.0.0", port=8888, reload=True)  # noqa: S104
