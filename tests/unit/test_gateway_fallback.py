"""Unit tests for the gateway fallback endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from api_gateway.fallback import router


@pytest.fixture
def app():
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestFallbackEndpoint:
    async def test_post_fallback_returns_503(self, client):
        response = await client.post("/fallback")
        assert response.status_code == 503

    async def test_post_fallback_returns_correct_message(self, client):
        response = await client.post("/fallback")
        assert response.text == "Chat is currently unavailable. Please try again later."

    async def test_post_fallback_content_type_is_text(self, client):
        response = await client.post("/fallback")
        assert "text/plain" in response.headers["content-type"]

    async def test_get_fallback_not_allowed(self, client):
        response = await client.get("/fallback")
        assert response.status_code == 405
