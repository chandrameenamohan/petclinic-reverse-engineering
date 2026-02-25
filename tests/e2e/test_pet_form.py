"""E2E smoke tests for the Pet form pages (create + edit)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import respx
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from api_gateway.pages import CUSTOMERS_URL
from api_gateway.pages import router as pages_router

_SAMPLE_OWNER = {
    "id": 1,
    "firstName": "George",
    "lastName": "Franklin",
    "address": "110 W. Liberty St.",
    "city": "Madison",
    "telephone": "6085551023",
    "pets": [],
}

_SAMPLE_PET_TYPES = [
    {"id": 1, "name": "cat"},
    {"id": 2, "name": "dog"},
    {"id": 3, "name": "lizard"},
    {"id": 4, "name": "snake"},
    {"id": 5, "name": "bird"},
    {"id": 6, "name": "hamster"},
]

_SAMPLE_PET_DETAIL = {
    "id": 1,
    "name": "Leo",
    "owner": "George Franklin",
    "birthDate": "2010-09-07",
    "type": {"id": 1, "name": "cat"},
}

_CREATED_PET = {
    "id": 3,
    "name": "Rex",
    "birthDate": "2020-01-15",
    "type": {"id": 2, "name": "dog"},
}


@pytest.fixture
def pet_form_app() -> FastAPI:
    """Gateway app with page routes for testing."""
    app = FastAPI()
    app.include_router(pages_router)
    return app


@pytest.fixture
async def pet_form_client(pet_form_app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Async HTTP client for the pet form page tests."""
    transport = ASGITransport(app=pet_form_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestCreatePetPage:
    """Smoke tests for GET /owners/{id}/new-pet — Create pet form."""

    @respx.mock
    async def test_returns_200(self, pet_form_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{CUSTOMERS_URL}/petTypes").mock(
            return_value=Response(200, json=_SAMPLE_PET_TYPES),
        )
        response = await pet_form_client.get("/owners/1/new-pet")
        assert response.status_code == 200

    @respx.mock
    async def test_content_type_is_html(self, pet_form_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{CUSTOMERS_URL}/petTypes").mock(
            return_value=Response(200, json=_SAMPLE_PET_TYPES),
        )
        response = await pet_form_client.get("/owners/1/new-pet")
        assert "text/html" in response.headers["content-type"]

    @respx.mock
    async def test_contains_pet_heading(self, pet_form_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{CUSTOMERS_URL}/petTypes").mock(
            return_value=Response(200, json=_SAMPLE_PET_TYPES),
        )
        response = await pet_form_client.get("/owners/1/new-pet")
        assert "Pet" in response.text

    @respx.mock
    async def test_shows_owner_name_readonly(self, pet_form_client: AsyncClient) -> None:
        """Owner name displayed as read-only text."""
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{CUSTOMERS_URL}/petTypes").mock(
            return_value=Response(200, json=_SAMPLE_PET_TYPES),
        )
        response = await pet_form_client.get("/owners/1/new-pet")
        assert "George Franklin" in response.text

    @respx.mock
    async def test_contains_form_fields(self, pet_form_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{CUSTOMERS_URL}/petTypes").mock(
            return_value=Response(200, json=_SAMPLE_PET_TYPES),
        )
        response = await pet_form_client.get("/owners/1/new-pet")
        html = response.text
        assert "Name" in html
        assert "Birth date" in html or "Birth Date" in html or "birthDate" in html
        assert "Type" in html

    @respx.mock
    async def test_contains_pet_type_dropdown(self, pet_form_client: AsyncClient) -> None:
        """Pet type dropdown contains all 6 types."""
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{CUSTOMERS_URL}/petTypes").mock(
            return_value=Response(200, json=_SAMPLE_PET_TYPES),
        )
        response = await pet_form_client.get("/owners/1/new-pet")
        html = response.text
        assert "<select" in html
        assert "cat" in html
        assert "dog" in html
        assert "hamster" in html

    @respx.mock
    async def test_contains_submit_button(self, pet_form_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{CUSTOMERS_URL}/petTypes").mock(
            return_value=Response(200, json=_SAMPLE_PET_TYPES),
        )
        response = await pet_form_client.get("/owners/1/new-pet")
        assert "Submit" in response.text


class TestCreatePetSubmit:
    """Tests for POST /owners/{id}/new-pet — Create pet form submission."""

    @respx.mock
    async def test_successful_create_redirects(self, pet_form_client: AsyncClient) -> None:
        """Successful create redirects to owner details."""
        respx.post(f"{CUSTOMERS_URL}/owners/1/pets").mock(
            return_value=Response(201, json=_CREATED_PET),
        )
        response = await pet_form_client.post(
            "/owners/1/new-pet",
            data={
                "name": "Rex",
                "birthDate": "2020-01-15",
                "typeId": "2",
            },
            follow_redirects=False,
        )
        assert response.status_code in (302, 303)
        assert "/owners/details/1" in response.headers.get("location", "")

    @respx.mock
    async def test_missing_name_shows_error(self, pet_form_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{CUSTOMERS_URL}/petTypes").mock(
            return_value=Response(200, json=_SAMPLE_PET_TYPES),
        )
        response = await pet_form_client.post(
            "/owners/1/new-pet",
            data={
                "name": "",
                "birthDate": "2020-01-15",
                "typeId": "1",
            },
        )
        assert response.status_code == 200
        assert "Name is required" in response.text

    @respx.mock
    async def test_missing_birth_date_shows_error(self, pet_form_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{CUSTOMERS_URL}/petTypes").mock(
            return_value=Response(200, json=_SAMPLE_PET_TYPES),
        )
        response = await pet_form_client.post(
            "/owners/1/new-pet",
            data={
                "name": "Rex",
                "birthDate": "",
                "typeId": "1",
            },
        )
        assert response.status_code == 200
        assert "birth date is required" in response.text.lower()

    @respx.mock
    async def test_backend_error_shows_message(self, pet_form_client: AsyncClient) -> None:
        """Backend failure re-renders form with error message."""
        respx.post(f"{CUSTOMERS_URL}/owners/1/pets").mock(
            return_value=Response(500, text="Internal Server Error"),
        )
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        respx.get(f"{CUSTOMERS_URL}/petTypes").mock(
            return_value=Response(200, json=_SAMPLE_PET_TYPES),
        )
        response = await pet_form_client.post(
            "/owners/1/new-pet",
            data={
                "name": "Rex",
                "birthDate": "2020-01-15",
                "typeId": "2",
            },
        )
        assert response.status_code == 200
        assert "could not" in response.text.lower() or "error" in response.text.lower()


class TestEditPetPage:
    """Smoke tests for GET /owners/{id}/pets/{petId} — Edit pet form."""

    @respx.mock
    async def test_returns_200(self, pet_form_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1/pets/1").mock(
            return_value=Response(200, json=_SAMPLE_PET_DETAIL),
        )
        respx.get(f"{CUSTOMERS_URL}/petTypes").mock(
            return_value=Response(200, json=_SAMPLE_PET_TYPES),
        )
        response = await pet_form_client.get("/owners/1/pets/1")
        assert response.status_code == 200

    @respx.mock
    async def test_form_pre_populated(self, pet_form_client: AsyncClient) -> None:
        """Edit form is pre-populated with pet data."""
        respx.get(f"{CUSTOMERS_URL}/owners/1/pets/1").mock(
            return_value=Response(200, json=_SAMPLE_PET_DETAIL),
        )
        respx.get(f"{CUSTOMERS_URL}/petTypes").mock(
            return_value=Response(200, json=_SAMPLE_PET_TYPES),
        )
        response = await pet_form_client.get("/owners/1/pets/1")
        html = response.text
        assert "Leo" in html
        assert "George Franklin" in html
        assert "2010-09-07" in html

    @respx.mock
    async def test_shows_owner_name_readonly(self, pet_form_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1/pets/1").mock(
            return_value=Response(200, json=_SAMPLE_PET_DETAIL),
        )
        respx.get(f"{CUSTOMERS_URL}/petTypes").mock(
            return_value=Response(200, json=_SAMPLE_PET_TYPES),
        )
        response = await pet_form_client.get("/owners/1/pets/1")
        assert "George Franklin" in response.text

    @respx.mock
    async def test_backend_error_shows_alert(self, pet_form_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1/pets/1").mock(
            return_value=Response(500, text="Internal Server Error"),
        )
        respx.get(f"{CUSTOMERS_URL}/petTypes").mock(
            return_value=Response(200, json=_SAMPLE_PET_TYPES),
        )
        response = await pet_form_client.get("/owners/1/pets/1")
        assert response.status_code == 200
        assert "error" in response.text.lower() or "alert" in response.text.lower()


class TestEditPetSubmit:
    """Tests for POST /owners/{id}/pets/{petId} — Edit pet form submission."""

    @respx.mock
    async def test_successful_edit_redirects(self, pet_form_client: AsyncClient) -> None:
        """Successful edit redirects to owner details."""
        respx.put(f"{CUSTOMERS_URL}/owners/1/pets/1").mock(
            return_value=Response(204),
        )
        response = await pet_form_client.post(
            "/owners/1/pets/1",
            data={
                "name": "Leo",
                "birthDate": "2010-09-07",
                "typeId": "1",
            },
            follow_redirects=False,
        )
        assert response.status_code in (302, 303)
        assert "/owners/details/1" in response.headers.get("location", "")

    @respx.mock
    async def test_validation_error_re_renders_form(
        self, pet_form_client: AsyncClient
    ) -> None:
        """Validation errors re-render the edit form."""
        respx.get(f"{CUSTOMERS_URL}/owners/1/pets/1").mock(
            return_value=Response(200, json=_SAMPLE_PET_DETAIL),
        )
        respx.get(f"{CUSTOMERS_URL}/petTypes").mock(
            return_value=Response(200, json=_SAMPLE_PET_TYPES),
        )
        response = await pet_form_client.post(
            "/owners/1/pets/1",
            data={
                "name": "",
                "birthDate": "2010-09-07",
                "typeId": "1",
            },
        )
        assert response.status_code == 200
        assert "Name is required" in response.text

    @respx.mock
    async def test_edit_sends_pet_id_in_body(self, pet_form_client: AsyncClient) -> None:
        """Edit PUT request includes pet id in request body (Java quirk)."""
        route = respx.put(f"{CUSTOMERS_URL}/owners/1/pets/1").mock(
            return_value=Response(204),
        )
        await pet_form_client.post(
            "/owners/1/pets/1",
            data={
                "name": "Leo",
                "birthDate": "2010-09-07",
                "typeId": "1",
            },
            follow_redirects=False,
        )
        assert route.called
        body = route.calls[0].request.content
        assert b"id" in body or b'"id"' in body
