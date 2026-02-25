"""Visits Service — FastAPI application entry point.

Mounts the visits router, initialises the async DB (tables + seed data),
exposes ``/actuator/health``, and runs on port 8082.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from shared.actuator import create_actuator_router
from shared.config import create_service_settings
from shared.database import Base, create_engine, create_session_factory, get_db_dependency
from shared.metrics import instrument_app
from shared.tracing import setup_tracing
from visits_service.models import Visit  # noqa: F401 — register table with metadata
from visits_service.routes import get_db
from visits_service.routes import router as visits_router
from visits_service.seed import seed_database


def create_app() -> FastAPI:
    """Create and configure the Visits FastAPI application."""
    settings = create_service_settings("visits-service")
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Visits DB tables created")

        # Seed data
        await seed_database(session_factory)

        yield

        # Shutdown
        await engine.dispose()
        logger.info("Visits DB engine disposed")

    app = FastAPI(title="Visits Service", lifespan=lifespan)

    # Override placeholder dependency with real session provider
    app.dependency_overrides[get_db] = get_db_dependency(session_factory)

    # --- Routers ---
    app.include_router(visits_router)
    app.include_router(create_actuator_router("visits-service"))

    # --- Metrics ---
    instrument_app(app)

    # --- Tracing ---
    setup_tracing(app, "visits-service", engine=engine, zipkin_endpoint=settings.zipkin_endpoint)

    logger.info("Visits service configured on port {}", settings.service_port)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("visits_service.main:app", host="0.0.0.0", port=8082, reload=True)  # noqa: S104
