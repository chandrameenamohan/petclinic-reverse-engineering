"""Discovery Server — FastAPI application entry point.

Lightweight in-memory service registry on port 8761.
Services register via POST /register and discover via GET /services/{name}.
"""

from __future__ import annotations

from fastapi import FastAPI
from loguru import logger

from discovery_server.registry import ServiceRegistry
from discovery_server.routes import router
from shared.actuator import create_actuator_router


def create_app() -> FastAPI:
    """Create and configure the Discovery Server application."""
    app = FastAPI(title="Discovery Server")

    # Each app instance gets its own registry (no global state)
    app.state.registry = ServiceRegistry()

    app.include_router(router)
    app.include_router(create_actuator_router("discovery-server"))

    logger.info("Discovery server configured")
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("discovery_server.main:app", host="0.0.0.0", port=8761, reload=True)  # noqa: S104
