"""API Gateway — FastAPI application entry point.

Mounts proxy routes, BFF aggregation, fallback endpoint, static files,
and ``/actuator/health``. Runs on port 8080.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger

from api_gateway.bff import configure_bff
from api_gateway.bff import router as bff_router
from api_gateway.fallback import router as fallback_router
from api_gateway.pages import configure_pages
from api_gateway.pages import router as pages_router
from api_gateway.proxy import configure_proxy
from api_gateway.proxy import router as proxy_router
from shared.actuator import create_actuator_router
from shared.config import create_service_settings
from shared.tracing import setup_tracing

_STATIC_DIR = Path(__file__).parent / "static"
_TEMPLATE_DIR = Path(__file__).parent / "templates"

templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))


def create_app() -> FastAPI:
    """Create and configure the API Gateway FastAPI application."""
    settings = create_service_settings("api-gateway")

    app = FastAPI(title="API Gateway")

    # Configure backend URLs from settings
    configure_proxy(settings)
    configure_bff(settings)
    configure_pages(settings)

    # --- Routers ---
    app.include_router(pages_router)
    app.include_router(bff_router)
    app.include_router(fallback_router)
    app.include_router(proxy_router)
    app.include_router(create_actuator_router("api-gateway"))

    # --- Tracing ---
    setup_tracing(app, "api-gateway", zipkin_endpoint=settings.zipkin_endpoint)

    # --- Static files (SPA) — must be last so catch-all doesn't shadow API routes ---
    if _STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")

    logger.info("API Gateway configured on port {}", settings.service_port)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api_gateway.main:app", host="0.0.0.0", port=8080, reload=True)  # noqa: S104
