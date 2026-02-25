"""E2E smoke tests for the Owner details page (GET /owners/details/{id})."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import respx
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from api_gateway.bff import CUSTOMERS_URL, VISITS_URL, owner_details_breaker
from api_gateway.pages import router as pages_router

_SAMPLE_OWNER = {
    "id": 1,
    "firstName": "George",
    "lastName": "Franklin",
    "address": "110 W. Liberty St.",
    "city": "Madison",
    "telephone": "6085551023",
    "pets": [
        {
            "id": 1,
            "name": "Leo",
            "birthDate": "2010-09-07",
            "type": {"id": 1, "name": "cat"},
        },
    ],
}

_SAMPLE_VISITS = {
    "items": [
        {"id": 1, "petId": 1, "date": "2013-01-01", "description": "rabies shot"},
        {"id": 4, "petId": 1, "date": "2013-01-04", "description": "spayed"},
    ],
}


@pytest.fixture(autouse=True)
def _reset_breaker() -> None:
    """Reset the circuit breaker between tests."""
    owner_details_breaker.close()


@pytest.fixture
def details_app() -> FastAPI:
    """Gateway app with page routes for testing."""
    app = FastAPI()
    app.include_router(pages_router)
    return app


@pytest.fixture
async def details_client(details_app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Async HTTP client for the owner details page tests."""
    transport = ASGITransport(app=details_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestOwnerDetailsPage:
    """Smoke tests for GET /owners/details/{id} — Owner details page."""

    @respx.mock
    async def test_returns_200(self, details_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{VISITS_URL}/pets/visits").mock(
            return_value=Response(200, json=_SAMPLE_VISITS),
        )
        response = await details_client.get("/owners/details/1")
        assert response.status_code == 200

    @respx.mock
    async def test_content_type_is_html(self, details_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{VISITS_URL}/pets/visits").mock(
            return_value=Response(200, json=_SAMPLE_VISITS),
        )
        response = await details_client.get("/owners/details/1")
        assert "text/html" in response.headers["content-type"]

    @respx.mock
    async def test_contains_owner_heading(self, details_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{VISITS_URL}/pets/visits").mock(
            return_value=Response(200, json=_SAMPLE_VISITS),
        )
        response = await details_client.get("/owners/details/1")
        assert "Owner Information" in response.text

    @respx.mock
    async def test_contains_owner_name(self, details_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{VISITS_URL}/pets/visits").mock(
            return_value=Response(200, json=_SAMPLE_VISITS),
        )
        response = await details_client.get("/owners/details/1")
        assert "George Franklin" in response.text

    @respx.mock
    async def test_contains_owner_address_city_telephone(
        self, details_client: AsyncClient
    ) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{VISITS_URL}/pets/visits").mock(
            return_value=Response(200, json=_SAMPLE_VISITS),
        )
        response = await details_client.get("/owners/details/1")
        html = response.text
        assert "110 W. Liberty St." in html
        assert "Madison" in html
        assert "6085551023" in html

    @respx.mock
    async def test_contains_edit_owner_link(self, details_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{VISITS_URL}/pets/visits").mock(
            return_value=Response(200, json=_SAMPLE_VISITS),
        )
        response = await details_client.get("/owners/details/1")
        html = response.text
        assert "/owners/1/edit" in html
        assert "Edit Owner" in html

    @respx.mock
    async def test_contains_add_pet_link(self, details_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{VISITS_URL}/pets/visits").mock(
            return_value=Response(200, json=_SAMPLE_VISITS),
        )
        response = await details_client.get("/owners/details/1")
        html = response.text
        assert "/owners/1/new-pet" in html
        assert "Add New Pet" in html

    @respx.mock
    async def test_contains_pet_name_as_link(
        self, details_client: AsyncClient
    ) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{VISITS_URL}/pets/visits").mock(
            return_value=Response(200, json=_SAMPLE_VISITS),
        )
        response = await details_client.get("/owners/details/1")
        html = response.text
        assert "Leo" in html
        assert "/owners/1/pets/1" in html

    @respx.mock
    async def test_contains_pet_birth_date_formatted(
        self, details_client: AsyncClient
    ) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{VISITS_URL}/pets/visits").mock(
            return_value=Response(200, json=_SAMPLE_VISITS),
        )
        response = await details_client.get("/owners/details/1")
        # Spec says "yyyy MMM dd" format, e.g. "2010 Sep 07"
        assert "2010 Sep 07" in response.text

    @respx.mock
    async def test_contains_pet_type(self, details_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{VISITS_URL}/pets/visits").mock(
            return_value=Response(200, json=_SAMPLE_VISITS),
        )
        response = await details_client.get("/owners/details/1")
        assert "cat" in response.text

    @respx.mock
    async def test_contains_visit_dates_and_descriptions(
        self, details_client: AsyncClient
    ) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{VISITS_URL}/pets/visits").mock(
            return_value=Response(200, json=_SAMPLE_VISITS),
        )
        response = await details_client.get("/owners/details/1")
        html = response.text
        assert "2013-01-01" in html
        assert "rabies shot" in html
        assert "2013-01-04" in html
        assert "spayed" in html

    @respx.mock
    async def test_contains_edit_pet_link(self, details_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{VISITS_URL}/pets/visits").mock(
            return_value=Response(200, json=_SAMPLE_VISITS),
        )
        response = await details_client.get("/owners/details/1")
        assert "Edit Pet" in response.text

    @respx.mock
    async def test_contains_add_visit_link(self, details_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{VISITS_URL}/pets/visits").mock(
            return_value=Response(200, json=_SAMPLE_VISITS),
        )
        response = await details_client.get("/owners/details/1")
        html = response.text
        assert "/owners/1/pets/1/visits" in html
        assert "Add Visit" in html

    @respx.mock
    async def test_pets_and_visits_heading(
        self, details_client: AsyncClient
    ) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{VISITS_URL}/pets/visits").mock(
            return_value=Response(200, json=_SAMPLE_VISITS),
        )
        response = await details_client.get("/owners/details/1")
        assert "Pets and Visits" in response.text

    @respx.mock
    async def test_owner_info_table_striped(
        self, details_client: AsyncClient
    ) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{VISITS_URL}/pets/visits").mock(
            return_value=Response(200, json=_SAMPLE_VISITS),
        )
        response = await details_client.get("/owners/details/1")
        assert "table-striped" in response.text

    @respx.mock
    async def test_backend_error_shows_error_message(
        self, details_client: AsyncClient
    ) -> None:
        """When customers service returns an error, show user-friendly message."""
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(500, text="Internal Server Error"),
        )
        response = await details_client.get("/owners/details/1")
        assert response.status_code == 200
        assert "Owner Information" in response.text

    @respx.mock
    async def test_visits_failure_still_shows_owner(
        self, details_client: AsyncClient
    ) -> None:
        """When visits service fails, owner shows with empty visits."""
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{VISITS_URL}/pets/visits").mock(
            return_value=Response(500, text="Internal Server Error"),
        )
        response = await details_client.get("/owners/details/1")
        assert response.status_code == 200
        html = response.text
        assert "George Franklin" in html
        assert "Leo" in html
        # No visit data since visits service failed
        assert "rabies shot" not in html
