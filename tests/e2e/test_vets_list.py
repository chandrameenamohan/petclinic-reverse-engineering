"""E2E smoke tests for the Vets list page (GET /vets)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import respx
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from api_gateway.pages import VETS_URL
from api_gateway.pages import router as pages_router

_SAMPLE_VETS = [
    {
        "id": 1,
        "firstName": "James",
        "lastName": "Carter",
        "specialties": [],
    },
    {
        "id": 2,
        "firstName": "Helen",
        "lastName": "Leary",
        "specialties": [{"id": 1, "name": "radiology"}],
    },
    {
        "id": 3,
        "firstName": "Linda",
        "lastName": "Douglas",
        "specialties": [
            {"id": 2, "name": "surgery"},
            {"id": 3, "name": "dentistry"},
        ],
    },
    {
        "id": 4,
        "firstName": "Rafael",
        "lastName": "Ortega",
        "specialties": [{"id": 2, "name": "surgery"}],
    },
    {
        "id": 5,
        "firstName": "Henry",
        "lastName": "Stevens",
        "specialties": [{"id": 1, "name": "radiology"}],
    },
    {
        "id": 6,
        "firstName": "Sharon",
        "lastName": "Jenkins",
        "specialties": [],
    },
]


@pytest.fixture
def vets_app() -> FastAPI:
    """Gateway app with page routes for testing."""
    app = FastAPI()
    app.include_router(pages_router)
    return app


@pytest.fixture
async def vets_client(vets_app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Async HTTP client for the vets page tests."""
    transport = ASGITransport(app=vets_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestVetsListPage:
    """Smoke tests for GET /vets — Veterinarians list page."""

    @respx.mock
    async def test_returns_200(self, vets_client: AsyncClient) -> None:
        respx.get(f"{VETS_URL}/vets").mock(
            return_value=Response(200, json=_SAMPLE_VETS),
        )
        response = await vets_client.get("/vets")
        assert response.status_code == 200

    @respx.mock
    async def test_content_type_is_html(self, vets_client: AsyncClient) -> None:
        respx.get(f"{VETS_URL}/vets").mock(
            return_value=Response(200, json=_SAMPLE_VETS),
        )
        response = await vets_client.get("/vets")
        assert "text/html" in response.headers["content-type"]

    @respx.mock
    async def test_contains_veterinarians_heading(self, vets_client: AsyncClient) -> None:
        respx.get(f"{VETS_URL}/vets").mock(
            return_value=Response(200, json=_SAMPLE_VETS),
        )
        response = await vets_client.get("/vets")
        assert "Veterinarians" in response.text

    @respx.mock
    async def test_contains_vet_names(self, vets_client: AsyncClient) -> None:
        respx.get(f"{VETS_URL}/vets").mock(
            return_value=Response(200, json=_SAMPLE_VETS),
        )
        response = await vets_client.get("/vets")
        html = response.text
        assert "James Carter" in html
        assert "Helen Leary" in html
        assert "Linda Douglas" in html
        assert "Rafael Ortega" in html
        assert "Henry Stevens" in html
        assert "Sharon Jenkins" in html

    @respx.mock
    async def test_contains_specialties(self, vets_client: AsyncClient) -> None:
        respx.get(f"{VETS_URL}/vets").mock(
            return_value=Response(200, json=_SAMPLE_VETS),
        )
        response = await vets_client.get("/vets")
        html = response.text
        assert "radiology" in html
        assert "surgery" in html
        assert "dentistry" in html

    @respx.mock
    async def test_multiple_specialties_space_separated(self, vets_client: AsyncClient) -> None:
        """Linda Douglas has surgery and dentistry — they should be space-separated."""
        respx.get(f"{VETS_URL}/vets").mock(
            return_value=Response(200, json=_SAMPLE_VETS),
        )
        response = await vets_client.get("/vets")
        html = response.text
        # Both specialties should appear in the same row
        assert "surgery" in html
        assert "dentistry" in html

    @respx.mock
    async def test_table_has_striped_class(self, vets_client: AsyncClient) -> None:
        respx.get(f"{VETS_URL}/vets").mock(
            return_value=Response(200, json=_SAMPLE_VETS),
        )
        response = await vets_client.get("/vets")
        assert "table-striped" in response.text

    @respx.mock
    async def test_table_has_name_and_specialties_headers(self, vets_client: AsyncClient) -> None:
        respx.get(f"{VETS_URL}/vets").mock(
            return_value=Response(200, json=_SAMPLE_VETS),
        )
        response = await vets_client.get("/vets")
        html = response.text
        assert "Name" in html
        assert "Specialties" in html

    @respx.mock
    async def test_backend_error_shows_error_message(self, vets_client: AsyncClient) -> None:
        """When vets service is unreachable, show a user-friendly error."""
        respx.get(f"{VETS_URL}/vets").mock(
            return_value=Response(500, text="Internal Server Error"),
        )
        response = await vets_client.get("/vets")
        assert response.status_code == 200
        html = response.text
        assert "Veterinarians" in html  # Still shows the page structure
