"""Unit tests for the gateway BFF endpoint: GET /api/gateway/owners/{ownerId}."""

from collections.abc import AsyncGenerator

import httpx
import pytest
import respx
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from httpx import Response as HttpxResponse

from api_gateway.bff import owner_details_breaker, router


@pytest.fixture(autouse=True)
def _reset_breaker() -> None:
    """Reset circuit breaker state between tests."""
    owner_details_breaker.close()


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# --- Sample data ---

OWNER_JSON = {
    "id": 6,
    "firstName": "Jean",
    "lastName": "Coleman",
    "address": "105 N. Lake St.",
    "city": "Monona",
    "telephone": "6085552654",
    "pets": [
        {
            "id": 7,
            "name": "Samantha",
            "birthDate": "2012-09-04",
            "type": {"id": 1, "name": "cat"},
        },
        {
            "id": 8,
            "name": "Max",
            "birthDate": "2012-09-04",
            "type": {"id": 1, "name": "cat"},
        },
    ],
}

VISITS_JSON = {
    "items": [
        {
            "id": 1,
            "petId": 7,
            "date": "2013-01-01",
            "description": "rabies shot",
        },
        {
            "id": 2,
            "petId": 8,
            "date": "2013-01-02",
            "description": "neutered",
        },
        {
            "id": 3,
            "petId": 7,
            "date": "2013-01-03",
            "description": "checkup",
        },
    ],
}


class TestBffHappyPath:
    """Owner with pets and visits merged correctly."""

    @respx.mock
    async def test_owner_with_visits_merged(self, client: AsyncClient) -> None:
        respx.get("http://localhost:8081/owners/6").mock(
            return_value=HttpxResponse(200, json=OWNER_JSON)
        )
        respx.get("http://localhost:8082/pets/visits").mock(
            return_value=HttpxResponse(200, json=VISITS_JSON)
        )

        response = await client.get("/api/gateway/owners/6")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 6
        assert data["firstName"] == "Jean"
        assert data["lastName"] == "Coleman"
        assert len(data["pets"]) == 2

        # Pet 7 should have 2 visits
        pet7 = next(p for p in data["pets"] if p["id"] == 7)
        assert len(pet7["visits"]) == 2
        assert pet7["visits"][0]["description"] == "rabies shot"
        assert pet7["visits"][1]["description"] == "checkup"

        # Pet 8 should have 1 visit
        pet8 = next(p for p in data["pets"] if p["id"] == 8)
        assert len(pet8["visits"]) == 1
        assert pet8["visits"][0]["description"] == "neutered"

    @respx.mock
    async def test_visits_batch_query_uses_comma_separated_ids(
        self, client: AsyncClient
    ) -> None:
        respx.get("http://localhost:8081/owners/6").mock(
            return_value=HttpxResponse(200, json=OWNER_JSON)
        )
        visits_route = respx.get("http://localhost:8082/pets/visits").mock(
            return_value=HttpxResponse(200, json={"items": []})
        )

        await client.get("/api/gateway/owners/6")

        assert visits_route.called
        request_url = str(visits_route.calls[0].request.url)
        assert "petId=7%2C8" in request_url or "petId=7,8" in request_url


class TestBffOwnerNoPets:
    """Owner with no pets should skip visits call."""

    @respx.mock
    async def test_owner_no_pets_skips_visits(self, client: AsyncClient) -> None:
        owner_no_pets = {**OWNER_JSON, "pets": []}
        respx.get("http://localhost:8081/owners/6").mock(
            return_value=HttpxResponse(200, json=owner_no_pets)
        )
        visits_route = respx.get("http://localhost:8082/pets/visits").mock(
            return_value=HttpxResponse(200, json={"items": []})
        )

        response = await client.get("/api/gateway/owners/6")

        assert response.status_code == 200
        assert response.json()["pets"] == []
        assert not visits_route.called


class TestBffVisitsFailureFallback:
    """When visits-service fails, return owner with empty visits (graceful degradation)."""

    @respx.mock
    async def test_visits_connection_error_returns_empty_visits(
        self, client: AsyncClient
    ) -> None:
        respx.get("http://localhost:8081/owners/6").mock(
            return_value=HttpxResponse(200, json=OWNER_JSON)
        )
        respx.get("http://localhost:8082/pets/visits").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        response = await client.get("/api/gateway/owners/6")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 6
        for pet in data["pets"]:
            assert pet["visits"] == []

    @respx.mock
    async def test_visits_500_returns_empty_visits(
        self, client: AsyncClient
    ) -> None:
        respx.get("http://localhost:8081/owners/6").mock(
            return_value=HttpxResponse(200, json=OWNER_JSON)
        )
        respx.get("http://localhost:8082/pets/visits").mock(
            return_value=HttpxResponse(500, json={"error": "Internal Server Error"})
        )

        response = await client.get("/api/gateway/owners/6")

        assert response.status_code == 200
        data = response.json()
        for pet in data["pets"]:
            assert pet["visits"] == []


class TestBffCircuitBreakerOpenState:
    """When the circuit breaker is OPEN, visits are skipped immediately."""

    @respx.mock
    async def test_breaker_open_returns_owner_with_empty_visits(
        self, client: AsyncClient
    ) -> None:
        """Pre-trip the breaker to OPEN, then verify visits call is never made."""
        # Force the breaker to OPEN state
        owner_details_breaker.open()

        respx.get("http://localhost:8081/owners/6").mock(
            return_value=HttpxResponse(200, json=OWNER_JSON)
        )
        visits_route = respx.get("http://localhost:8082/pets/visits").mock(
            return_value=HttpxResponse(200, json=VISITS_JSON)
        )

        response = await client.get("/api/gateway/owners/6")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 6
        assert data["firstName"] == "Jean"
        # Visits should be empty — breaker is open, no call made
        for pet in data["pets"]:
            assert pet["visits"] == []
        # The visits endpoint should NOT have been called
        assert not visits_route.called

    @respx.mock
    async def test_repeated_failures_trip_breaker(
        self, client: AsyncClient
    ) -> None:
        """After fail_max failures, breaker trips and visits are empty."""
        respx.get("http://localhost:8081/owners/6").mock(
            return_value=HttpxResponse(200, json=OWNER_JSON)
        )
        respx.get("http://localhost:8082/pets/visits").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        # Make fail_max (5) requests to trip the breaker
        for _ in range(owner_details_breaker.fail_max):
            response = await client.get("/api/gateway/owners/6")
            assert response.status_code == 200

        # Breaker should now be open
        assert owner_details_breaker.current_state == "open"

        # Next request should still succeed with empty visits
        response = await client.get("/api/gateway/owners/6")
        assert response.status_code == 200
        data = response.json()
        for pet in data["pets"]:
            assert pet["visits"] == []


class TestBffOwnerNotFound:
    """When customers-service returns null/empty for owner, forward that response."""

    @respx.mock
    async def test_owner_not_found_returns_null(self, client: AsyncClient) -> None:
        respx.get("http://localhost:8081/owners/999").mock(
            return_value=HttpxResponse(200, content=b"null")
        )

        response = await client.get("/api/gateway/owners/999")

        # Java returns 200 with null body for Optional.empty()
        assert response.status_code == 200
        assert response.json() is None

    @respx.mock
    async def test_customers_service_down_returns_502(
        self, client: AsyncClient
    ) -> None:
        respx.get("http://localhost:8081/owners/6").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        response = await client.get("/api/gateway/owners/6")

        assert response.status_code == 502
