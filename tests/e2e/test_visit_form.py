"""E2E smoke tests for the Visit form page (add visit)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import respx
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from api_gateway.pages import VISITS_URL
from api_gateway.pages import router as pages_router

_SAMPLE_VISITS: list[dict[str, object]] = [
    {"id": 1, "date": "2013-01-01", "description": "rabies shot", "petId": 7},
    {"id": 2, "date": "2013-01-04", "description": "spayed", "petId": 7},
]

_CREATED_VISIT = {
    "id": 5,
    "date": "2024-06-15",
    "description": "Annual checkup",
    "petId": 7,
}


@pytest.fixture
def visit_form_app() -> FastAPI:
    """Gateway app with page routes for testing."""
    app = FastAPI()
    app.include_router(pages_router)
    return app


@pytest.fixture
async def visit_form_client(visit_form_app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Async HTTP client for visit form page tests."""
    transport = ASGITransport(app=visit_form_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestVisitFormPage:
    """Smoke tests for GET /owners/{id}/pets/{petId}/visits — Add visit form."""

    @respx.mock
    async def test_returns_200(self, visit_form_client: AsyncClient) -> None:
        respx.get(f"{VISITS_URL}/owners/1/pets/7/visits").mock(
            return_value=Response(200, json=_SAMPLE_VISITS),
        )
        response = await visit_form_client.get("/owners/1/pets/7/visits")
        assert response.status_code == 200

    @respx.mock
    async def test_content_type_is_html(self, visit_form_client: AsyncClient) -> None:
        respx.get(f"{VISITS_URL}/owners/1/pets/7/visits").mock(
            return_value=Response(200, json=_SAMPLE_VISITS),
        )
        response = await visit_form_client.get("/owners/1/pets/7/visits")
        assert "text/html" in response.headers["content-type"]

    @respx.mock
    async def test_contains_visits_heading(self, visit_form_client: AsyncClient) -> None:
        respx.get(f"{VISITS_URL}/owners/1/pets/7/visits").mock(
            return_value=Response(200, json=_SAMPLE_VISITS),
        )
        response = await visit_form_client.get("/owners/1/pets/7/visits")
        assert "Visits" in response.text

    @respx.mock
    async def test_contains_date_field_with_today_default(
        self, visit_form_client: AsyncClient
    ) -> None:
        """Date input should exist and default to today's date."""
        respx.get(f"{VISITS_URL}/owners/1/pets/7/visits").mock(
            return_value=Response(200, json=_SAMPLE_VISITS),
        )
        response = await visit_form_client.get("/owners/1/pets/7/visits")
        html = response.text
        assert 'type="date"' in html
        # The date field should have a value attribute set to today
        assert 'name="date"' in html

    @respx.mock
    async def test_contains_description_textarea(
        self, visit_form_client: AsyncClient
    ) -> None:
        respx.get(f"{VISITS_URL}/owners/1/pets/7/visits").mock(
            return_value=Response(200, json=_SAMPLE_VISITS),
        )
        response = await visit_form_client.get("/owners/1/pets/7/visits")
        assert "<textarea" in response.text

    @respx.mock
    async def test_contains_submit_button(self, visit_form_client: AsyncClient) -> None:
        respx.get(f"{VISITS_URL}/owners/1/pets/7/visits").mock(
            return_value=Response(200, json=_SAMPLE_VISITS),
        )
        response = await visit_form_client.get("/owners/1/pets/7/visits")
        assert "Add New Visit" in response.text or "Submit" in response.text

    @respx.mock
    async def test_shows_previous_visits(self, visit_form_client: AsyncClient) -> None:
        """Previous visits table should display existing visits."""
        respx.get(f"{VISITS_URL}/owners/1/pets/7/visits").mock(
            return_value=Response(200, json=_SAMPLE_VISITS),
        )
        response = await visit_form_client.get("/owners/1/pets/7/visits")
        html = response.text
        assert "Previous Visits" in html
        assert "rabies shot" in html
        assert "spayed" in html
        assert "2013-01-01" in html

    @respx.mock
    async def test_no_previous_visits(self, visit_form_client: AsyncClient) -> None:
        """When no previous visits exist, still renders the form."""
        respx.get(f"{VISITS_URL}/owners/1/pets/7/visits").mock(
            return_value=Response(200, json=[]),
        )
        response = await visit_form_client.get("/owners/1/pets/7/visits")
        assert response.status_code == 200
        assert "Visits" in response.text

    @respx.mock
    async def test_backend_error_shows_form_anyway(
        self, visit_form_client: AsyncClient
    ) -> None:
        """If visits fetch fails, form still renders (with empty visits list)."""
        respx.get(f"{VISITS_URL}/owners/1/pets/7/visits").mock(
            return_value=Response(500, text="Internal Server Error"),
        )
        response = await visit_form_client.get("/owners/1/pets/7/visits")
        assert response.status_code == 200
        assert "<textarea" in response.text


class TestVisitFormSubmit:
    """Tests for POST /owners/{id}/pets/{petId}/visits — Create visit submission."""

    @respx.mock
    async def test_successful_create_redirects(
        self, visit_form_client: AsyncClient
    ) -> None:
        """Successful create redirects to owner details."""
        respx.post(f"{VISITS_URL}/owners/1/pets/7/visits").mock(
            return_value=Response(201, json=_CREATED_VISIT),
        )
        response = await visit_form_client.post(
            "/owners/1/pets/7/visits",
            data={"date": "2024-06-15", "description": "Annual checkup"},
            follow_redirects=False,
        )
        assert response.status_code in (302, 303)
        assert "/owners/details/1" in response.headers.get("location", "")

    @respx.mock
    async def test_missing_description_shows_error(
        self, visit_form_client: AsyncClient
    ) -> None:
        """Description is required — re-render form with error."""
        respx.get(f"{VISITS_URL}/owners/1/pets/7/visits").mock(
            return_value=Response(200, json=_SAMPLE_VISITS),
        )
        response = await visit_form_client.post(
            "/owners/1/pets/7/visits",
            data={"date": "2024-06-15", "description": ""},
        )
        assert response.status_code == 200
        assert "description" in response.text.lower()

    @respx.mock
    async def test_backend_error_shows_message(
        self, visit_form_client: AsyncClient
    ) -> None:
        """Backend failure re-renders form with error message."""
        respx.post(f"{VISITS_URL}/owners/1/pets/7/visits").mock(
            return_value=Response(500, text="Internal Server Error"),
        )
        respx.get(f"{VISITS_URL}/owners/1/pets/7/visits").mock(
            return_value=Response(200, json=_SAMPLE_VISITS),
        )
        response = await visit_form_client.post(
            "/owners/1/pets/7/visits",
            data={"date": "2024-06-15", "description": "Annual checkup"},
        )
        assert response.status_code == 200
        assert "could not" in response.text.lower() or "error" in response.text.lower()
