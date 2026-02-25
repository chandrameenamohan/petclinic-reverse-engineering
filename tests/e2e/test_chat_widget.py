"""E2E smoke tests for the Chat Widget UI and API integration."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api_gateway.pages import router as pages_router

CHAT_JS_PATH = Path(__file__).resolve().parents[2] / "api_gateway" / "static" / "js" / "chat.js"


@pytest.fixture
def chat_app() -> FastAPI:
    """Minimal gateway app for chat widget testing."""
    app = FastAPI()
    app.include_router(pages_router)
    return app


@pytest.fixture
async def chat_client(chat_app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Async HTTP client for chat widget tests."""
    transport = ASGITransport(app=chat_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestChatWidgetPresence:
    """Verify the chat widget HTML is rendered in the base template."""

    async def test_chatbox_container_present(self, chat_client: AsyncClient) -> None:
        response = await chat_client.get("/")
        assert response.status_code == 200
        assert 'id="chatbox"' in response.text

    async def test_chat_header_text(self, chat_client: AsyncClient) -> None:
        response = await chat_client.get("/")
        assert "Chat with Us!" in response.text

    async def test_chat_input_field(self, chat_client: AsyncClient) -> None:
        response = await chat_client.get("/")
        assert 'id="chatbox-input"' in response.text

    async def test_send_button_present(self, chat_client: AsyncClient) -> None:
        response = await chat_client.get("/")
        html = response.text
        assert "Send" in html

    async def test_marked_js_included(self, chat_client: AsyncClient) -> None:
        response = await chat_client.get("/")
        assert "marked" in response.text

    async def test_chat_js_included(self, chat_client: AsyncClient) -> None:
        response = await chat_client.get("/")
        assert "chat.js" in response.text

    async def test_chat_messages_container(self, chat_client: AsyncClient) -> None:
        response = await chat_client.get("/")
        assert 'id="chatbox-messages"' in response.text

    async def test_chatbox_toggle_header(self, chat_client: AsyncClient) -> None:
        response = await chat_client.get("/")
        assert 'id="chatbox-header"' in response.text


class TestChatWidgetApiIntegration:
    """Verify chat.js contains the API call, localStorage, and error fallback."""

    @pytest.fixture(autouse=True)
    def _load_js(self) -> None:
        self.js_content = CHAT_JS_PATH.read_text()

    def test_fetch_endpoint(self) -> None:
        assert "/api/genai/chatclient" in self.js_content

    def test_fetch_method_post(self) -> None:
        assert '"POST"' in self.js_content or "'POST'" in self.js_content

    def test_content_type_json(self) -> None:
        assert "application/json" in self.js_content

    def test_json_stringify_body(self) -> None:
        assert "JSON.stringify" in self.js_content

    def test_localstorage_save(self) -> None:
        assert "localStorage.setItem" in self.js_content

    def test_localstorage_load(self) -> None:
        assert "localStorage.getItem" in self.js_content

    def test_storage_key(self) -> None:
        assert "petclinic_chat" in self.js_content

    def test_error_fallback_message(self) -> None:
        assert "Chat is currently unavailable" in self.js_content

    def test_response_text_handling(self) -> None:
        assert "response.text()" in self.js_content
