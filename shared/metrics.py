"""Prometheus metrics for petclinic services.

Provides:
- ``instrument_app(app)`` — attach ``prometheus-fastapi-instrumentator`` and
  expose ``/actuator/prometheus``.
- Custom Histogram metrics (``petclinic_owner_seconds``, ``petclinic_pet_seconds``,
  ``petclinic_visit_seconds``) matching the Java ``@Timed`` annotations.
- An Instrumentator hook that maps route handlers to the correct histogram
  without decorating endpoint functions (avoids cross-module annotation issues).
"""

from __future__ import annotations

from fastapi import FastAPI
from prometheus_client import Histogram
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator.metrics import Info

# ---------------------------------------------------------------------------
# Custom histograms — equivalent to Java @Timed("petclinic.*") annotations
# ---------------------------------------------------------------------------

OWNER_HISTOGRAM = Histogram(
    "petclinic_owner_seconds",
    "Owner endpoint request duration",
    ["method", "exception"],
)

PET_HISTOGRAM = Histogram(
    "petclinic_pet_seconds",
    "Pet endpoint request duration",
    ["method", "exception"],
)

VISIT_HISTOGRAM = Histogram(
    "petclinic_visit_seconds",
    "Visit endpoint request duration",
    ["method", "exception"],
)

# ---------------------------------------------------------------------------
# Route → histogram mapping
# ---------------------------------------------------------------------------

# Maps (HTTP_METHOD, path_template) → (histogram, metric_method_name)
_ROUTE_METRICS: dict[tuple[str, str], tuple[Histogram, str]] = {
    # Owner endpoints  (customers-service)
    ("GET", "/petTypes"): (OWNER_HISTOGRAM, "getPetTypes"),
    ("GET", "/owners"): (OWNER_HISTOGRAM, "listOwners"),
    ("GET", "/owners/{owner_id}"): (OWNER_HISTOGRAM, "getOwner"),
    ("PUT", "/owners/{owner_id}"): (OWNER_HISTOGRAM, "updateOwner"),
    ("POST", "/owners"): (OWNER_HISTOGRAM, "createOwner"),
    # Pet endpoints  (customers-service)
    ("POST", "/owners/{owner_id}/pets"): (PET_HISTOGRAM, "createPet"),
    ("GET", "/owners/{owner_id}/pets/{pet_id}"): (PET_HISTOGRAM, "getPet"),
    ("PUT", "/owners/{owner_id}/pets/{pet_id}"): (PET_HISTOGRAM, "updatePet"),
    # Visit endpoints  (visits-service)
    ("POST", "/owners/{owner_id}/pets/{pet_id}/visits"): (VISIT_HISTOGRAM, "createVisit"),
    ("GET", "/owners/{owner_id}/pets/{pet_id}/visits"): (VISIT_HISTOGRAM, "getVisitsForPet"),
    ("GET", "/pets/visits"): (VISIT_HISTOGRAM, "getVisitsForPets"),
}


def _petclinic_metrics_hook(info: Info) -> None:
    """Instrumentator hook that records custom petclinic_*_seconds metrics."""
    request = info.request
    response = info.response
    if response is None:
        return

    # Resolve the route template from the ASGI scope
    route = request.scope.get("route")
    if route is None:
        return
    path_template: str = getattr(route, "path", "")
    http_method: str = request.method

    key = (http_method, path_template)
    mapping = _ROUTE_METRICS.get(key)
    if mapping is None:
        return

    histogram, method_name = mapping
    duration: float = info.modified_duration

    # Determine exception label from status code
    status_code = response.status_code
    if status_code < 400:
        exception_name = "none"
    elif status_code < 500:
        exception_name = "HTTPException"
    else:
        exception_name = "Exception"

    histogram.labels(method=method_name, exception=exception_name).observe(duration)


# ---------------------------------------------------------------------------
# App instrumentation helper
# ---------------------------------------------------------------------------


def instrument_app(app: FastAPI) -> None:
    """Attach standard HTTP metrics, custom petclinic histograms, and expose ``/actuator/prometheus``."""
    instrumentator = Instrumentator()
    instrumentator.add(_petclinic_metrics_hook)
    instrumentator.instrument(app).expose(app, endpoint="/actuator/prometheus")
