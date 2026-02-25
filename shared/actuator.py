"""Shared actuator router — ``/actuator/health`` and ``/actuator/info``.

Each service calls ``create_actuator_router(service_name)`` to get a pre-configured
APIRouter and includes it in its FastAPI application.
"""

from __future__ import annotations

import os

from fastapi import APIRouter


def create_actuator_router(service_name: str) -> APIRouter:
    """Return an APIRouter with ``/actuator/health`` and ``/actuator/info``."""
    router = APIRouter(prefix="/actuator", tags=["actuator"])

    @router.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "UP"}

    @router.get("/info")
    async def info() -> dict[str, dict[str, str]]:
        return {
            "build": {
                "artifact": service_name,
                "version": "1.0.0",
            },
            "git": {
                "branch": os.getenv("GIT_BRANCH", "main"),
                "commit": os.getenv("GIT_COMMIT", "unknown"),
            },
        }

    return router
