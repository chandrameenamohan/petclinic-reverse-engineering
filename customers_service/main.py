"""Customers Service — FastAPI application entry point.

Mounts the customers router, initialises the async DB (tables + seed data),
exposes ``/actuator/health``, and runs on port 8081.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from customers_service.models import Owner, Pet, PetType  # noqa: F401 — register tables with metadata
from customers_service.routes import get_db
from customers_service.routes import router as customers_router
from customers_service.seed import seed_database
from shared.actuator import create_actuator_router
from shared.config import create_service_settings
from shared.database import Base, create_engine, create_session_factory, get_db_dependency
from shared.metrics import instrument_app
from shared.tracing import setup_tracing


def create_app() -> FastAPI:
    """Create and configure the Customers FastAPI application."""
    settings = create_service_settings("customers-service")
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Customers DB tables created")

        # Seed data
        await seed_database(session_factory)

        yield

        # Shutdown
        await engine.dispose()
        logger.info("Customers DB engine disposed")

    app = FastAPI(title="Customers Service", lifespan=lifespan)

    # Override placeholder dependency with real session provider
    app.dependency_overrides[get_db] = get_db_dependency(session_factory)

    # --- Routers ---
    app.include_router(customers_router)
    app.include_router(create_actuator_router("customers-service"))

    # --- Metrics ---
    instrument_app(app)

    # --- Tracing ---
    setup_tracing(app, "customers-service", engine=engine, zipkin_endpoint=settings.zipkin_endpoint)

    logger.info("Customers service configured on port {}", settings.service_port)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("customers_service.main:app", host="0.0.0.0", port=8081, reload=True)  # noqa: S104
