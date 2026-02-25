"""E2E smoke tests for the Welcome page."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api_gateway.pages import router as pages_router


@pytest.fixture
def welcome_app() -> FastAPI:
    """Minimal gateway app with page routes for testing."""
    app = FastAPI()
    app.include_router(pages_router)
    return app


@pytest.fixture
async def welcome_client(welcome_app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Async HTTP client for the welcome page tests."""
    transport = ASGITransport(app=welcome_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestWelcomePage:
    """Smoke tests for GET / — Welcome page."""

    async def test_returns_200(self, welcome_client: AsyncClient) -> None:
        response = await welcome_client.get("/")
        assert response.status_code == 200

    async def test_content_type_is_html(self, welcome_client: AsyncClient) -> None:
        response = await welcome_client.get("/")
        assert "text/html" in response.headers["content-type"]

    async def test_contains_welcome_heading(self, welcome_client: AsyncClient) -> None:
        response = await welcome_client.get("/")
        assert "Welcome to Petclinic" in response.text

    async def test_contains_hero_image(self, welcome_client: AsyncClient) -> None:
        response = await welcome_client.get("/")
        assert "pets.png" in response.text

    async def test_contains_nav_links(self, welcome_client: AsyncClient) -> None:
        response = await welcome_client.get("/")
        html = response.text
        assert "/owners" in html
        assert "/vets" in html
