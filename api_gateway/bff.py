"""BFF aggregation endpoint — merges owner data with visits.

``GET /api/gateway/owners/{ownerId}`` fetches an owner from customers-service,
batch-fetches visits from visits-service, and merges visits into each pet.

Circuit breaker ``getOwnerDetails`` wraps the visits call; on failure the
owner is returned with empty visits (graceful degradation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pybreaker
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel, Field

from api_gateway.circuit_breaker import call_breaker_async

if TYPE_CHECKING:
    from shared.config import BaseServiceSettings

# Module-level service URLs — configurable via configure_bff().
CUSTOMERS_URL = "http://localhost:8081"
VISITS_URL = "http://localhost:8082"

# Dedicated circuit breaker for the visits call in the BFF endpoint.
owner_details_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
    name="getOwnerDetails",
)

router = APIRouter(prefix="/api/gateway", tags=["gateway"])


# --- Pydantic DTOs (gateway-local, not shared) ---


class VisitDetail(BaseModel):
    """Visit detail in the aggregated owner response."""

    id: int | None = None
    pet_id: int = Field(..., alias="petId")
    date: str
    description: str | None = None

    model_config = {"populate_by_name": True}


class PetTypeDetail(BaseModel):
    """Pet type in the aggregated owner response (name only, matching Spring BFF)."""

    name: str


class GatewayPetDetail(BaseModel):
    """Pet with visits in the aggregated owner response."""

    id: int
    name: str
    birth_date: str | None = Field(None, alias="birthDate")
    type: PetTypeDetail | None = None
    visits: list[VisitDetail] = []

    model_config = {"populate_by_name": True}


class GatewayOwnerDetails(BaseModel):
    """Aggregated owner response with pets and visits merged."""

    id: int
    first_name: str = Field(..., alias="firstName")
    last_name: str = Field(..., alias="lastName")
    address: str
    city: str
    telephone: str
    pets: list[GatewayPetDetail] = []

    model_config = {"populate_by_name": True}


def configure_bff(settings: BaseServiceSettings) -> None:
    """Update service URLs from settings."""
    global CUSTOMERS_URL, VISITS_URL  # noqa: PLW0603
    CUSTOMERS_URL = settings.customers_service_url
    VISITS_URL = settings.visits_service_url


@router.get("/owners/{owner_id}", response_model=None)
async def get_owner_details(owner_id: int) -> GatewayOwnerDetails | JSONResponse:
    """BFF endpoint: fetch owner + batch-fetch visits + merge into pets.

    If the visits service is unavailable (circuit breaker or error), the
    owner is returned with empty visits arrays (graceful degradation).
    If the customers service is unavailable, returns 502.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Step 1: Fetch owner from customers-service
        try:
            owner_resp = await client.get(f"{CUSTOMERS_URL}/owners/{owner_id}")
        except httpx.HTTPError as exc:
            logger.error("Customers service error for owner {}: {}", owner_id, exc)
            return JSONResponse(status_code=502, content={"detail": "Bad Gateway"})

        # Handle null/not-found owner (Java Optional returns 200 + null)
        if owner_resp.content == b"null" or owner_resp.content == b"":
            return JSONResponse(status_code=200, content=None)

        owner_data = owner_resp.json()
        owner = GatewayOwnerDetails(**owner_data)

        # Step 2: Batch-fetch visits with circuit breaker
        pet_ids = [pet.id for pet in owner.pets]
        visits = await _fetch_visits_safe(client, pet_ids)

        # Step 3: Merge visits into pets
        for pet in owner.pets:
            pet.visits = [v for v in visits if v.pet_id == pet.id]

        return owner


async def _fetch_visits_safe(
    client: httpx.AsyncClient,
    pet_ids: list[int],
) -> list[VisitDetail]:
    """Fetch visits with circuit breaker fallback — returns empty list on failure."""
    if not pet_ids:
        return []
    try:
        return await call_breaker_async(
            owner_details_breaker,
            lambda: _fetch_visits(client, pet_ids),
        )
    except Exception:
        logger.warning("Visits fetch failed for pets {}; returning empty visits", pet_ids)
        return []


async def _fetch_visits(
    client: httpx.AsyncClient,
    pet_ids: list[int],
) -> list[VisitDetail]:
    """Fetch visits from visits-service for the given pet IDs."""
    ids_param = ",".join(str(pid) for pid in pet_ids)
    resp = await client.get(
        f"{VISITS_URL}/pets/visits",
        params={"petId": ids_param},
    )
    resp.raise_for_status()
    data = resp.json()
    return [VisitDetail(**v) for v in data.get("items", [])]
