"""E2E smoke tests for the Owner form pages (create + edit)."""

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


@pytest.fixture
def form_app() -> FastAPI:
    """Gateway app with page routes for testing."""
    app = FastAPI()
    app.include_router(pages_router)
    return app


@pytest.fixture
async def form_client(form_app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Async HTTP client for the owner form page tests."""
    transport = ASGITransport(app=form_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestCreateOwnerPage:
    """Smoke tests for GET /owners/new — Create owner form."""

    async def test_returns_200(self, form_client: AsyncClient) -> None:
        response = await form_client.get("/owners/new")
        assert response.status_code == 200

    async def test_content_type_is_html(self, form_client: AsyncClient) -> None:
        response = await form_client.get("/owners/new")
        assert "text/html" in response.headers["content-type"]

    async def test_contains_owner_heading(self, form_client: AsyncClient) -> None:
        response = await form_client.get("/owners/new")
        assert "Owner" in response.text

    async def test_contains_form_fields(self, form_client: AsyncClient) -> None:
        response = await form_client.get("/owners/new")
        html = response.text
        assert "First name" in html or "firstName" in html
        assert "Last name" in html or "lastName" in html
        assert "Address" in html
        assert "City" in html
        assert "Telephone" in html

    async def test_contains_submit_button(self, form_client: AsyncClient) -> None:
        response = await form_client.get("/owners/new")
        assert "Submit" in response.text

    async def test_form_has_post_method(self, form_client: AsyncClient) -> None:
        response = await form_client.get("/owners/new")
        assert 'method="post"' in response.text.lower()


class TestCreateOwnerSubmit:
    """Tests for POST /owners/new — Create owner form submission."""

    @respx.mock
    async def test_successful_create_redirects(self, form_client: AsyncClient) -> None:
        """Successful create redirects to owners list."""
        respx.post(f"{CUSTOMERS_URL}/owners").mock(
            return_value=Response(201, json=_SAMPLE_OWNER),
        )
        response = await form_client.post(
            "/owners/new",
            data={
                "firstName": "George",
                "lastName": "Franklin",
                "address": "110 W. Liberty St.",
                "city": "Madison",
                "telephone": "6085551023",
            },
            follow_redirects=False,
        )
        assert response.status_code in (302, 303)

    @respx.mock
    async def test_successful_create_redirects_to_owner_details(
        self, form_client: AsyncClient
    ) -> None:
        """After creating, redirect to the new owner's details page."""
        respx.post(f"{CUSTOMERS_URL}/owners").mock(
            return_value=Response(201, json=_SAMPLE_OWNER),
        )
        response = await form_client.post(
            "/owners/new",
            data={
                "firstName": "George",
                "lastName": "Franklin",
                "address": "110 W. Liberty St.",
                "city": "Madison",
                "telephone": "6085551023",
            },
            follow_redirects=False,
        )
        assert "/owners/details/1" in response.headers.get("location", "")

    async def test_missing_first_name_shows_error(
        self, form_client: AsyncClient
    ) -> None:
        """Missing first name re-renders form with validation error."""
        response = await form_client.post(
            "/owners/new",
            data={
                "firstName": "",
                "lastName": "Franklin",
                "address": "110 W. Liberty St.",
                "city": "Madison",
                "telephone": "6085551023",
            },
        )
        assert response.status_code == 200
        assert "First name is required" in response.text

    async def test_missing_last_name_shows_error(
        self, form_client: AsyncClient
    ) -> None:
        """Missing last name re-renders form with validation error."""
        response = await form_client.post(
            "/owners/new",
            data={
                "firstName": "George",
                "lastName": "",
                "address": "110 W. Liberty St.",
                "city": "Madison",
                "telephone": "6085551023",
            },
        )
        assert response.status_code == 200
        assert "Last name is required" in response.text

    async def test_missing_address_shows_error(
        self, form_client: AsyncClient
    ) -> None:
        response = await form_client.post(
            "/owners/new",
            data={
                "firstName": "George",
                "lastName": "Franklin",
                "address": "",
                "city": "Madison",
                "telephone": "6085551023",
            },
        )
        assert response.status_code == 200
        assert "Address is required" in response.text

    async def test_missing_telephone_shows_error(
        self, form_client: AsyncClient
    ) -> None:
        response = await form_client.post(
            "/owners/new",
            data={
                "firstName": "George",
                "lastName": "Franklin",
                "address": "110 W. Liberty St.",
                "city": "Madison",
                "telephone": "",
            },
        )
        assert response.status_code == 200
        assert "Telephone is required" in response.text

    async def test_non_digit_telephone_shows_error(
        self, form_client: AsyncClient
    ) -> None:
        response = await form_client.post(
            "/owners/new",
            data={
                "firstName": "George",
                "lastName": "Franklin",
                "address": "110 W. Liberty St.",
                "city": "Madison",
                "telephone": "abc123",
            },
        )
        assert response.status_code == 200
        assert "digits" in response.text.lower()


class TestEditOwnerPage:
    """Smoke tests for GET /owners/{id}/edit — Edit owner form."""

    @respx.mock
    async def test_returns_200(self, form_client: AsyncClient) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        response = await form_client.get("/owners/1/edit")
        assert response.status_code == 200

    @respx.mock
    async def test_contains_form_pre_populated(
        self, form_client: AsyncClient
    ) -> None:
        """Edit form is pre-populated with owner data."""
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(200, json=_SAMPLE_OWNER),
        )
        response = await form_client.get("/owners/1/edit")
        html = response.text
        assert "George" in html
        assert "Franklin" in html
        assert "110 W. Liberty St." in html
        assert "Madison" in html
        assert "6085551023" in html

    @respx.mock
    async def test_backend_error_shows_alert(
        self, form_client: AsyncClient
    ) -> None:
        respx.get(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(500, text="Internal Server Error"),
        )
        response = await form_client.get("/owners/1/edit")
        assert response.status_code == 200
        # Should show some error message
        assert "error" in response.text.lower() or "alert" in response.text.lower()


class TestEditOwnerSubmit:
    """Tests for POST /owners/{id}/edit — Edit owner form submission."""

    @respx.mock
    async def test_successful_edit_redirects(
        self, form_client: AsyncClient
    ) -> None:
        """Successful edit redirects to owner details page."""
        respx.put(f"{CUSTOMERS_URL}/owners/1").mock(
            return_value=Response(204),
        )
        response = await form_client.post(
            "/owners/1/edit",
            data={
                "firstName": "George",
                "lastName": "Franklin",
                "address": "110 W. Liberty St.",
                "city": "Madison",
                "telephone": "6085551023",
            },
            follow_redirects=False,
        )
        assert response.status_code in (302, 303)
        assert "/owners/details/1" in response.headers.get("location", "")

    async def test_validation_error_re_renders_form(
        self, form_client: AsyncClient
    ) -> None:
        """Validation errors re-render the edit form."""
        response = await form_client.post(
            "/owners/1/edit",
            data={
                "firstName": "",
                "lastName": "Franklin",
                "address": "110 W. Liberty St.",
                "city": "Madison",
                "telephone": "6085551023",
            },
        )
        assert response.status_code == 200
        assert "First name is required" in response.text
