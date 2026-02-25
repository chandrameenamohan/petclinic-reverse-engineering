"""Unit tests for the GenAI service main.py — app creation, health, chat router."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def mock_openai_response():
    """Create a mock OpenAI chat completion response."""
    choice = MagicMock()
    choice.message.content = "Hello from GenAI!"
    choice.message.tool_calls = None
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.fixture(autouse=True)
def _clear_chat_history():
    """Clear chat memory before each test."""
    import genai_service.chat as chat_mod

    chat_mod.chat_history.clear()
    yield
    chat_mod.chat_history.clear()


@pytest.fixture
def genai_app():
    """Create the GenAI FastAPI app."""
    from genai_service.main import create_app

    return create_app()


@pytest.fixture
async def genai_client(genai_app):
    """Async HTTP client for the GenAI service."""
    transport = ASGITransport(app=genai_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestHealthEndpoint:
    """Tests for GET /actuator/health."""

    async def test_health_returns_200(self, genai_client):
        response = await genai_client.get("/actuator/health")
        assert response.status_code == 200

    async def test_health_returns_status_up(self, genai_client):
        response = await genai_client.get("/actuator/health")
        data = response.json()
        assert data == {"status": "UP"}

    async def test_health_returns_json(self, genai_client):
        response = await genai_client.get("/actuator/health")
        assert "application/json" in response.headers["content-type"]


class TestInfoEndpoint:
    """Tests for GET /actuator/info."""

    async def test_info_returns_correct_artifact(self, genai_client):
        response = await genai_client.get("/actuator/info")
        assert response.status_code == 200
        data = response.json()
        assert data["build"]["artifact"] == "genai-service"
        assert data["build"]["version"] == "1.0.0"
        assert "git" in data


class TestChatRouterIntegration:
    """Tests that the chat router is properly mounted in the app."""

    @patch("genai_service.chat.get_openai_client")
    async def test_chatclient_endpoint_is_mounted(
        self, mock_get_client, genai_client, mock_openai_response
    ):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        mock_get_client.return_value = mock_client

        response = await genai_client.post("/chatclient", json="Hello")
        assert response.status_code == 200

    @patch("genai_service.chat.get_openai_client")
    async def test_chatclient_returns_plain_text(
        self, mock_get_client, genai_client, mock_openai_response
    ):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        mock_get_client.return_value = mock_client

        response = await genai_client.post("/chatclient", json="Hello")
        assert "text/plain" in response.headers["content-type"]
        assert response.text == "Hello from GenAI!"


class TestAppFactory:
    """Tests for the create_app factory function."""

    def test_create_app_returns_fastapi_instance(self):
        from fastapi import FastAPI

        from genai_service.main import create_app

        app = create_app()
        assert isinstance(app, FastAPI)

    def test_create_app_has_title(self):
        from genai_service.main import create_app

        app = create_app()
        assert app.title == "GenAI Service"
