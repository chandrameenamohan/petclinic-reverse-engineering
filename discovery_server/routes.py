"""Discovery server routes — POST /register and GET /services/{service_name}."""

from __future__ import annotations

from fastapi import APIRouter, Request

from discovery_server.registry import ServiceRegistry
from discovery_server.schemas import RegisterRequest, RegisterResponse, ServiceInstance

router = APIRouter()


def get_registry(request: Request) -> ServiceRegistry:
    """Retrieve the registry from app state."""
    registry: ServiceRegistry = request.app.state.registry
    return registry


@router.post("/register")
async def register(body: RegisterRequest, request: Request) -> RegisterResponse:
    """Register a service instance in the discovery registry."""
    registry = get_registry(request)
    registry.register(body.service_name, body.host, body.port)
    return RegisterResponse(status="registered")


@router.get("/services/{service_name}")
async def get_services(service_name: str, request: Request) -> list[ServiceInstance]:
    """Return all registered instances for a given service name."""
    registry = get_registry(request)
    return registry.get_instances(service_name)
