"""Admin Server — service health monitoring dashboard on port 9090.

Polls ``/actuator/health`` from all registered services and returns
an aggregated status via ``GET /dashboard``.
"""

from __future__ import annotations

import os

import httpx
from fastapi import FastAPI
from loguru import logger

from shared.actuator import create_actuator_router


def _default_services() -> dict[str, str]:
    """Build service URL map, honouring environment variable overrides."""
    return {
        "customers-service": os.environ.get(
            "CUSTOMERS_SERVICE_URL", "http://localhost:8081"
        ),
        "visits-service": os.environ.get(
            "VISITS_SERVICE_URL", "http://localhost:8082"
        ),
        "vets-service": os.environ.get(
            "VETS_SERVICE_URL", "http://localhost:8083"
        ),
        "genai-service": os.environ.get(
            "GENAI_SERVICE_URL", "http://localhost:8084"
        ),
        "api-gateway": os.environ.get(
            "API_GATEWAY_URL", "http://localhost:8080"
        ),
    }


def create_app(
    *,
    services: dict[str, str] | None = None,
) -> FastAPI:
    """Create and configure the Admin Server application."""
    resolved_services = services if services is not None else _default_services()

    app = FastAPI(title="Admin Dashboard")
    app.state.services = resolved_services

    @app.get("/dashboard")
    async def dashboard() -> dict[str, dict[str, str]]:
        results: dict[str, dict[str, str]] = {}
        async with httpx.AsyncClient(timeout=5.0) as client:
            for name, url in app.state.services.items():
                try:
                    resp = await client.get(f"{url}/actuator/health")
                    results[name] = resp.json()
                except Exception:  # noqa: BLE001
                    results[name] = {"status": "DOWN"}
        return results

    app.include_router(create_actuator_router("admin-server"))

    logger.info("Admin server configured (services={})", list(resolved_services))
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("admin_server.main:app", host="0.0.0.0", port=9090, reload=True)  # noqa: S104
