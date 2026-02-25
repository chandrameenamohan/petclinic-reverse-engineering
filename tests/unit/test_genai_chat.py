"""Unit tests for the GenAI POST /chatclient endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def mock_openai_response():
    """Create a mock OpenAI chat completion response."""
    choice = MagicMock()
    choice.message.content = "Hello! I'm the Petclinic AI assistant."
    choice.message.tool_calls = None
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.fixture(autouse=True)
def _clear_chat_history():
    """Clear chat memory before each test to avoid cross-test contamination."""
    import genai_service.chat as chat_mod

    chat_mod.chat_history.clear()
    yield
    chat_mod.chat_history.clear()


@pytest.fixture
def app(mock_openai_response):
    from fastapi import FastAPI

    from genai_service.chat import router

    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestChatEndpoint:
    @patch("genai_service.chat.get_openai_client")
    async def test_post_chatclient_returns_200(self, mock_get_client, client, mock_openai_response):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        mock_get_client.return_value = mock_client

        response = await client.post("/chatclient", json="What owners do you have?")
        assert response.status_code == 200

    @patch("genai_service.chat.get_openai_client")
    async def test_post_chatclient_returns_plain_text(self, mock_get_client, client, mock_openai_response):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        mock_get_client.return_value = mock_client

        response = await client.post("/chatclient", json="What owners do you have?")
        assert "text/plain" in response.headers["content-type"]
        assert response.text == "Hello! I'm the Petclinic AI assistant."

    @patch("genai_service.chat.get_openai_client")
    async def test_post_chatclient_calls_openai_with_gpt4o_mini(self, mock_get_client, client, mock_openai_response):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        mock_get_client.return_value = mock_client

        await client.post("/chatclient", json="Hello")

        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "gpt-4o-mini"

    @patch("genai_service.chat.get_openai_client")
    async def test_post_chatclient_uses_temperature_07(self, mock_get_client, client, mock_openai_response):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        mock_get_client.return_value = mock_client

        await client.post("/chatclient", json="Hello")

        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["temperature"] == 0.7

    @patch("genai_service.chat.get_openai_client")
    async def test_post_chatclient_includes_user_message(self, mock_get_client, client, mock_openai_response):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        mock_get_client.return_value = mock_client

        await client.post("/chatclient", json="List all owners")

        call_kwargs = mock_client.chat.completions.create.call_args
        messages = call_kwargs.kwargs["messages"]
        user_messages = [m for m in messages if m["role"] == "user"]
        assert any(m["content"] == "List all owners" for m in user_messages)

    @patch("genai_service.chat.get_openai_client")
    async def test_post_chatclient_error_returns_fallback_message(self, mock_get_client, client):
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API error"))
        mock_get_client.return_value = mock_client

        response = await client.post("/chatclient", json="Hello")
        assert response.status_code == 200
        assert response.text == "Chat is currently unavailable. Please try again later."

    async def test_get_chatclient_not_allowed(self, client):
        response = await client.get("/chatclient")
        assert response.status_code == 405

    @patch("genai_service.chat.get_openai_client")
    async def test_post_chatclient_accepts_json_string_body(self, mock_get_client, client, mock_openai_response):
        """The endpoint should accept a raw JSON string (e.g., "What owners?")."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        mock_get_client.return_value = mock_client

        response = await client.post(
            "/chatclient",
            content='"What owners do you have?"',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200


class TestSystemPrompt:
    """Tests for the hardcoded system prompt from the spec."""

    @patch("genai_service.chat.get_openai_client")
    async def test_system_prompt_is_first_message(
        self, mock_get_client: AsyncMock, client: AsyncClient, mock_openai_response: MagicMock
    ) -> None:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        mock_get_client.return_value = mock_client

        await client.post("/chatclient", json="Hello")

        call_kwargs = mock_client.chat.completions.create.call_args
        messages = call_kwargs.kwargs["messages"]
        assert messages[0]["role"] == "system"

    @patch("genai_service.chat.get_openai_client")
    async def test_system_prompt_contains_spring_petclinic(
        self, mock_get_client: AsyncMock, client: AsyncClient, mock_openai_response: MagicMock
    ) -> None:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        mock_get_client.return_value = mock_client

        await client.post("/chatclient", json="Hello")

        call_kwargs = mock_client.chat.completions.create.call_args
        messages = call_kwargs.kwargs["messages"]
        system_msg = messages[0]["content"]
        assert "Spring Petclinic" in system_msg
        assert "veterinarian pet clinic" in system_msg

    @patch("genai_service.chat.get_openai_client")
    async def test_system_prompt_exact_text(
        self, mock_get_client: AsyncMock, client: AsyncClient, mock_openai_response: MagicMock
    ) -> None:
        from genai_service.chat import SYSTEM_PROMPT

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        mock_get_client.return_value = mock_client

        await client.post("/chatclient", json="Hello")

        call_kwargs = mock_client.chat.completions.create.call_args
        messages = call_kwargs.kwargs["messages"]
        assert messages[0]["content"] == SYSTEM_PROMPT
        # Verify key phrases from the spec
        assert "friendly AI assistant" in SYSTEM_PROMPT
        assert "professional manner" in SYSTEM_PROMPT
        assert "followup question" in SYSTEM_PROMPT
        assert "additional data that was not returned" in SYSTEM_PROMPT
        assert "total number of all vets" in SYSTEM_PROMPT


class TestChatMemory:
    """Tests for in-memory chat history (last 10 messages)."""

    @patch("genai_service.chat.get_openai_client")
    async def test_chat_memory_stores_user_message(
        self, mock_get_client: AsyncMock, client: AsyncClient, mock_openai_response: MagicMock
    ) -> None:
        import genai_service.chat as chat_mod

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        mock_get_client.return_value = mock_client

        await client.post("/chatclient", json="Hello there")

        assert any(m["role"] == "user" and m["content"] == "Hello there" for m in chat_mod.chat_history)

    @patch("genai_service.chat.get_openai_client")
    async def test_chat_memory_stores_assistant_reply(
        self, mock_get_client: AsyncMock, client: AsyncClient, mock_openai_response: MagicMock
    ) -> None:
        import genai_service.chat as chat_mod

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        mock_get_client.return_value = mock_client

        await client.post("/chatclient", json="Hello")

        assert any(
            m["role"] == "assistant" and m["content"] == "Hello! I'm the Petclinic AI assistant."
            for m in chat_mod.chat_history
        )

    @patch("genai_service.chat.get_openai_client")
    async def test_chat_memory_includes_previous_messages(
        self, mock_get_client: AsyncMock, client: AsyncClient, mock_openai_response: MagicMock
    ) -> None:
        """Second call should include the first conversation turn in messages."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        mock_get_client.return_value = mock_client

        # First message
        await client.post("/chatclient", json="First question")
        # Second message
        await client.post("/chatclient", json="Second question")

        # Check the second call's messages include the first turn
        second_call_kwargs = mock_client.chat.completions.create.call_args_list[1]
        messages = second_call_kwargs.kwargs["messages"]
        # Should have: system + user(first) + assistant(first reply) + user(second)
        roles = [m["role"] for m in messages]
        assert roles[0] == "system"
        assert "user" in roles[1:]
        user_contents = [m["content"] for m in messages if m["role"] == "user"]
        assert "First question" in user_contents
        assert "Second question" in user_contents

    @patch("genai_service.chat.get_openai_client")
    async def test_chat_memory_limits_to_last_10_messages(
        self, mock_get_client: AsyncMock, client: AsyncClient, mock_openai_response: MagicMock
    ) -> None:
        """Only the last 10 messages (user+assistant) should be sent to OpenAI."""

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        mock_get_client.return_value = mock_client

        # Send 7 messages (each produces user+assistant = 14 messages total in history)
        for i in range(7):
            await client.post("/chatclient", json=f"Message {i}")

        # The 7th call should only include last 10 history messages + system prompt
        last_call_kwargs = mock_client.chat.completions.create.call_args
        messages = last_call_kwargs.kwargs["messages"]
        # First message is always system prompt
        assert messages[0]["role"] == "system"
        # The rest should be at most 10 messages (history)
        history_messages = messages[1:]
        assert len(history_messages) <= 10

    @patch("genai_service.chat.get_openai_client")
    async def test_chat_memory_preserves_order(
        self, mock_get_client: AsyncMock, client: AsyncClient, mock_openai_response: MagicMock
    ) -> None:
        """Messages should be in chronological order: user, assistant, user, assistant..."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        mock_get_client.return_value = mock_client

        await client.post("/chatclient", json="First")
        await client.post("/chatclient", json="Second")

        last_call_kwargs = mock_client.chat.completions.create.call_args
        messages = last_call_kwargs.kwargs["messages"]
        # Skip system message, check alternating pattern
        history = messages[1:]
        for i, msg in enumerate(history):
            expected_role = "user" if i % 2 == 0 else "assistant"
            assert msg["role"] == expected_role, f"Message {i} should be {expected_role}, got {msg['role']}"
