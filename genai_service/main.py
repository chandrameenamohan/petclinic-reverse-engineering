"""GenAI Service — FastAPI application entry point.

Mounts the chat router (POST /chatclient) and health endpoint.
Loads vet data into vector store on startup.
Runs on port 8084.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from genai_service.chat import router as chat_router
from genai_service.vector_store import initialize as init_vector_store
from shared.actuator import create_actuator_router
from shared.config import create_service_settings
from shared.tracing import setup_tracing


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    """Startup: load vet data into vector store."""
    try:
        await init_vector_store()
    except Exception:
        logger.warning("Failed to initialize vector store — listVets will use HTTP fallback")
    yield


def create_app() -> FastAPI:
    """Create and configure the GenAI FastAPI application."""
    settings = create_service_settings("genai-service")
    app = FastAPI(title="GenAI Service", lifespan=lifespan)

    # --- Routers ---
    app.include_router(chat_router)
    app.include_router(create_actuator_router("genai-service"))

    # --- Tracing ---
    setup_tracing(app, "genai-service", zipkin_endpoint=settings.zipkin_endpoint)

    logger.info("GenAI service configured")
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("genai_service.main:app", host="0.0.0.0", port=8084, reload=True)  # noqa: S104
