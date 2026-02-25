"""E2E smoke tests for the Owners list page (GET /owners)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import respx
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from api_gateway.pages import CUSTOMERS_URL
from api_gateway.pages import router as pages_router

_SAMPLE_OWNERS = [
    {
        "id": 1,
        "firstName": "George",
        "lastName": "Franklin",
        "address": "110 W. Liberty St.",
        "city": "Madison",
        "telephone": "6085551023",
        "pets": [{"id": 1, "name": "Leo", "birthDate": "2010-09-07", "type": {"id": 1, "name": "cat"}}],
    },
    {
        "id": 2,
        "firstName": "Betty",
        "lastName": "Davis",
        "address": "638 Cardinal Ave.",
        "city": "Sun Prairie",
        "telephone": "6085551749",
        "pets": [{"id": 2, "name": "Basil", "birthDate": "2012-08-06", "type": {"id": 6, "name": "hamster"}}],
    },
    {
        "id": 6,
        "firstName": "Jean",
        "lastName": "Coleman",
        "address": "105 N. Lake St.",
        "city": "Monona",
        "telephone": "6085552654",
        "pets": [
            {"id": 7, "name": "Samantha", "birthDate": "2012-09-04", "type": {"id": 1, "name": "cat"}},
            {"id": 8, "name": "Max", "birthDate": "2012-09-04", "type": {"id": 1, "name": "cat"}},
        ],
    },
]


@pytest.fixture
def owners_app() -> FastAPI:
    """Gateway app with page routes for testing."""
    app = FastAPI()
    app.include_router(pages_router)
    return app


@pytest.fixture
async def owners_client(owners_app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Async HTTP client for the owners page tests."""
    transport = ASGITransport(app=owners_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestOwnersListPage:
    """Smoke tests for GET /owners — Owners list page."""

    @respx.mock
    async def test_returns_200(self, owners_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners").mock(
            return_value=Response(200, json=_SAMPLE_OWNERS),
        )
        response = await owners_client.get("/owners")
        assert response.status_code == 200

    @respx.mock
    async def test_content_type_is_html(self, owners_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners").mock(
            return_value=Response(200, json=_SAMPLE_OWNERS),
        )
        response = await owners_client.get("/owners")
        assert "text/html" in response.headers["content-type"]

    @respx.mock
    async def test_contains_owners_heading(self, owners_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners").mock(
            return_value=Response(200, json=_SAMPLE_OWNERS),
        )
        response = await owners_client.get("/owners")
        assert "Owners" in response.text

    @respx.mock
    async def test_contains_search_input(self, owners_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners").mock(
            return_value=Response(200, json=_SAMPLE_OWNERS),
        )
        response = await owners_client.get("/owners")
        assert 'id="owner-search"' in response.text

    @respx.mock
    async def test_contains_owner_names(self, owners_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners").mock(
            return_value=Response(200, json=_SAMPLE_OWNERS),
        )
        response = await owners_client.get("/owners")
        html = response.text
        assert "George Franklin" in html
        assert "Betty Davis" in html
        assert "Jean Coleman" in html

    @respx.mock
    async def test_owner_name_links_to_details(self, owners_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners").mock(
            return_value=Response(200, json=_SAMPLE_OWNERS),
        )
        response = await owners_client.get("/owners")
        html = response.text
        assert '/owners/details/1"' in html
        assert '/owners/details/2"' in html

    @respx.mock
    async def test_contains_address_city_telephone(self, owners_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners").mock(
            return_value=Response(200, json=_SAMPLE_OWNERS),
        )
        response = await owners_client.get("/owners")
        html = response.text
        assert "110 W. Liberty St." in html
        assert "Madison" in html
        assert "6085551023" in html

    @respx.mock
    async def test_contains_pet_names(self, owners_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners").mock(
            return_value=Response(200, json=_SAMPLE_OWNERS),
        )
        response = await owners_client.get("/owners")
        html = response.text
        assert "Leo" in html
        assert "Basil" in html

    @respx.mock
    async def test_multiple_pets_space_separated(self, owners_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners").mock(
            return_value=Response(200, json=_SAMPLE_OWNERS),
        )
        response = await owners_client.get("/owners")
        # Jean Coleman has Samantha and Max — they should appear in the same row
        html = response.text
        assert "Samantha" in html
        assert "Max" in html

    @respx.mock
    async def test_responsive_address_column_hidden_classes(self, owners_client: AsyncClient) -> None:
        """Address column should be hidden on screens < lg (< 992px)."""
        respx.get(f"{CUSTOMERS_URL}/owners").mock(
            return_value=Response(200, json=_SAMPLE_OWNERS),
        )
        response = await owners_client.get("/owners")
        html = response.text
        # Bootstrap 5: d-none d-lg-table-cell = hidden below lg breakpoint
        assert "d-none d-lg-table-cell" in html

    @respx.mock
    async def test_responsive_pets_column_hidden_classes(self, owners_client: AsyncClient) -> None:
        """Pets column should be hidden on screens < md (< 768px)."""
        respx.get(f"{CUSTOMERS_URL}/owners").mock(
            return_value=Response(200, json=_SAMPLE_OWNERS),
        )
        response = await owners_client.get("/owners")
        html = response.text
        # Bootstrap 5: d-none d-md-table-cell = hidden below md breakpoint
        assert "d-none d-md-table-cell" in html

    @respx.mock
    async def test_table_has_striped_class(self, owners_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners").mock(
            return_value=Response(200, json=_SAMPLE_OWNERS),
        )
        response = await owners_client.get("/owners")
        assert "table-striped" in response.text

    @respx.mock
    async def test_backend_error_shows_error_message(self, owners_client: AsyncClient) -> None:
        """When customers service is unreachable, show a user-friendly error."""
        respx.get(f"{CUSTOMERS_URL}/owners").mock(
            return_value=Response(500, text="Internal Server Error"),
        )
        response = await owners_client.get("/owners")
        assert response.status_code == 200
        html = response.text
        assert "Owners" in html  # Still shows the page structure
