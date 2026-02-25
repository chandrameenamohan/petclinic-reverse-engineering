"""In-memory service registry for discovery server."""

from __future__ import annotations

from discovery_server.schemas import ServiceInstance


class ServiceRegistry:
    """Thread-safe in-memory registry of service instances.

    Each service name maps to a list of unique (host, port) instances.
    """

    def __init__(self) -> None:
        self._services: dict[str, list[ServiceInstance]] = {}

    def register(self, service_name: str, host: str, port: int) -> None:
        """Register a service instance. Duplicates are ignored."""
        instance = ServiceInstance(host=host, port=port)
        if service_name not in self._services:
            self._services[service_name] = []
        # Deduplicate by (host, port)
        if instance not in self._services[service_name]:
            self._services[service_name].append(instance)

    def get_instances(self, service_name: str) -> list[ServiceInstance]:
        """Return all registered instances for a service (empty list if unknown)."""
        return self._services.get(service_name, [])
