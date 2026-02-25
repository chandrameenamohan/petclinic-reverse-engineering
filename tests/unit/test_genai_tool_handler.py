"""Unit tests for GenAI tool handler — dispatch + tool call loop."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient


class TestDispatchTool:
    """Test dispatch_tool routes to correct backend endpoints."""

    @pytest.fixture(autouse=True)
    def _set_service_url(self):
        """Ensure a known customers-service URL for tests."""
        import genai_service.tool_handler as handler

        handler.CUSTOMERS_SERVICE_URL = "http://localhost:8081"
        handler.VETS_SERVICE_URL = "http://localhost:8083"

    @pytest.mark.parametrize("mock_response_json", [[{"id": 1, "firstName": "George"}]])
    async def test_list_owners_calls_get_owners(self, mock_response_json):
        from genai_service.tool_handler import dispatch_tool

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_json
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await dispatch_tool("listOwners", {}, mock_client)
        mock_client.get.assert_called_once_with("http://localhost:8081/owners")
        assert result == mock_response_json

    async def test_add_owner_calls_post_owners(self):
        from genai_service.tool_handler import dispatch_tool

        owner_data = {
            "firstName": "Jane",
            "lastName": "Doe",
            "address": "123 Main St",
            "city": "Springfield",
            "telephone": "1234567890",
        }
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 99, **owner_data}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=mock_response)

        result = await dispatch_tool("addOwnerToPetclinic", owner_data, mock_client)
        mock_client.post.assert_called_once_with(
            "http://localhost:8081/owners", json=owner_data
        )
        assert result["id"] == 99

    async def test_add_pet_to_owner_calls_post_pets(self):
        from genai_service.tool_handler import dispatch_tool

        args = {"ownerId": 1, "name": "Rex", "birthDate": "2020-01-01", "typeId": 2}
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 10, "name": "Rex"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = AsyncMock(return_value=mock_response)

        result = await dispatch_tool("addPetToOwner", args, mock_client)
        # ownerId should be extracted from args, rest sent as body
        mock_client.post.assert_called_once_with(
            "http://localhost:8081/owners/1/pets",
            json={"name": "Rex", "birthDate": "2020-01-01", "typeId": 2},
        )
        assert result["name"] == "Rex"

    async def test_list_vets_uses_vector_store_when_initialized(self):
        """listVets uses chromadb similarity search when vector store is initialized."""
        from genai_service.tool_handler import dispatch_tool

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        vet_docs = ['{"firstName": "James", "lastName": "Carter", "specialties": []}']

        with patch("genai_service.vector_store.search_vets", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = vet_docs
            result = await dispatch_tool("listVets", {}, mock_client)

        mock_search.assert_called_once_with(None)
        mock_client.get.assert_not_called()
        assert result == vet_docs

    async def test_list_vets_with_filter_passes_filter_to_vector_store(self):
        """listVets passes filter args to search_vets for similarity search."""
        from genai_service.tool_handler import dispatch_tool

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        vet_filter = {"specialties": [{"name": "radiology"}]}
        vet_docs = ['{"firstName": "Helen", "lastName": "Leary", "specialties": [{"name": "radiology"}]}']

        with patch("genai_service.vector_store.search_vets", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = vet_docs
            result = await dispatch_tool("listVets", vet_filter, mock_client)

        mock_search.assert_called_once_with(vet_filter)
        mock_client.get.assert_not_called()
        assert result == vet_docs

    async def test_list_vets_falls_back_to_http_when_vector_store_empty(self):
        """listVets falls back to GET /vets when vector store returns empty results."""
        from genai_service.tool_handler import dispatch_tool

        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": 1, "firstName": "James"}]
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("genai_service.vector_store.search_vets", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []
            result = await dispatch_tool("listVets", {}, mock_client)

        mock_client.get.assert_called_once_with("http://localhost:8083/vets")
        assert result == [{"id": 1, "firstName": "James"}]

    async def test_unknown_tool_returns_error(self):
        from genai_service.tool_handler import dispatch_tool

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        result = await dispatch_tool("unknownTool", {}, mock_client)
        assert "error" in result

    async def test_http_error_returns_error_dict(self):
        from genai_service.tool_handler import dispatch_tool

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        result = await dispatch_tool("listOwners", {}, mock_client)
        assert "error" in result


class TestHandleToolCalls:
    """Test the tool call loop processes tool calls and re-submits to OpenAI."""

    def _make_tool_call(self, tool_id: str, name: str, arguments: dict) -> MagicMock:
        tc = MagicMock()
        tc.id = tool_id
        tc.function.name = name
        tc.function.arguments = json.dumps(arguments)
        return tc

    def _make_message(
        self,
        content: str | None = None,
        tool_calls: list | None = None,
    ) -> MagicMock:
        msg = MagicMock()
        msg.content = content
        msg.tool_calls = tool_calls
        msg.role = "assistant"
        msg.model_dump.return_value = {
            "role": "assistant",
            "content": content,
            "tool_calls": (
                [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ]
                if tool_calls
                else None
            ),
        }
        return msg

    async def test_single_tool_call_dispatched_and_returned_to_llm(self):
        from genai_service.tool_handler import handle_tool_calls

        tool_call = self._make_tool_call("call_1", "listOwners", {})
        initial_msg = self._make_message(tool_calls=[tool_call])

        # Final response with no tool calls
        final_msg = self._make_message(content="Here are the owners: George Franklin")
        final_response = MagicMock()
        final_response.choices = [MagicMock(message=final_msg)]

        mock_openai = AsyncMock()
        mock_openai.chat.completions.create = AsyncMock(return_value=final_response)

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_response = MagicMock()
        mock_http_response.json.return_value = [{"id": 1, "firstName": "George"}]
        mock_http_response.raise_for_status = MagicMock()
        mock_http_client.get = AsyncMock(return_value=mock_http_response)

        messages = [{"role": "system", "content": "system"}, {"role": "user", "content": "list owners"}]

        result = await handle_tool_calls(
            openai_client=mock_openai,
            http_client=mock_http_client,
            message=initial_msg,
            messages=messages,
        )

        assert result.content == "Here are the owners: George Franklin"
        mock_openai.chat.completions.create.assert_called_once()

    async def test_multi_step_tool_calls(self):
        """If the LLM returns more tool_calls after the first round, loop continues."""
        from genai_service.tool_handler import handle_tool_calls

        # First tool call
        tc1 = self._make_tool_call("call_1", "listOwners", {})
        msg1 = self._make_message(tool_calls=[tc1])

        # Second tool call in response
        tc2 = self._make_tool_call("call_2", "addPetToOwner", {
            "ownerId": 1, "name": "Rex", "birthDate": "2020-01-01", "typeId": 2,
        })
        msg2 = self._make_message(tool_calls=[tc2])
        resp2 = MagicMock()
        resp2.choices = [MagicMock(message=msg2)]

        # Final response
        msg3 = self._make_message(content="Done! Added Rex.")
        resp3 = MagicMock()
        resp3.choices = [MagicMock(message=msg3)]

        mock_openai = AsyncMock()
        mock_openai.chat.completions.create = AsyncMock(side_effect=[resp2, resp3])

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_response = MagicMock()
        mock_http_response.json.return_value = [{"id": 1}]
        mock_http_response.raise_for_status = MagicMock()
        mock_http_client.get = AsyncMock(return_value=mock_http_response)
        mock_http_client.post = AsyncMock(return_value=mock_http_response)

        messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "q"}]

        result = await handle_tool_calls(
            openai_client=mock_openai,
            http_client=mock_http_client,
            message=msg1,
            messages=messages,
        )

        assert result.content == "Done! Added Rex."
        assert mock_openai.chat.completions.create.call_count == 2

    async def test_max_iterations_prevents_infinite_loop(self):
        """Tool call loop should stop after MAX_TOOL_ITERATIONS to prevent infinite loops."""
        from genai_service.tool_handler import handle_tool_calls

        tc = self._make_tool_call("call_1", "listOwners", {})
        looping_msg = self._make_message(tool_calls=[tc])
        looping_response = MagicMock()
        looping_response.choices = [MagicMock(message=looping_msg)]

        mock_openai = AsyncMock()
        mock_openai.chat.completions.create = AsyncMock(return_value=looping_response)

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_response = MagicMock()
        mock_http_response.json.return_value = []
        mock_http_response.raise_for_status = MagicMock()
        mock_http_client.get = AsyncMock(return_value=mock_http_response)

        messages = [{"role": "system", "content": "sys"}]

        await handle_tool_calls(
            openai_client=mock_openai,
            http_client=mock_http_client,
            message=looping_msg,
            messages=messages,
        )

        # Should stop after max iterations (default 10)
        assert mock_openai.chat.completions.create.call_count <= 10

    async def test_tool_results_include_tool_call_id(self):
        """Each tool result message must reference the tool_call_id."""
        from genai_service.tool_handler import handle_tool_calls

        tc = self._make_tool_call("call_abc", "listOwners", {})
        msg = self._make_message(tool_calls=[tc])

        final_msg = self._make_message(content="Done")
        final_response = MagicMock()
        final_response.choices = [MagicMock(message=final_msg)]

        mock_openai = AsyncMock()
        mock_openai.chat.completions.create = AsyncMock(return_value=final_response)

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_response = MagicMock()
        mock_http_response.json.return_value = []
        mock_http_response.raise_for_status = MagicMock()
        mock_http_client.get = AsyncMock(return_value=mock_http_response)

        messages = [{"role": "system", "content": "sys"}]

        await handle_tool_calls(
            openai_client=mock_openai,
            http_client=mock_http_client,
            message=msg,
            messages=messages,
        )

        # Check the messages sent to OpenAI contain a tool result with matching ID
        call_kwargs = mock_openai.chat.completions.create.call_args
        sent_messages = call_kwargs.kwargs["messages"]
        tool_result_msgs = [m for m in sent_messages if m.get("role") == "tool"]
        assert len(tool_result_msgs) == 1
        assert tool_result_msgs[0]["tool_call_id"] == "call_abc"


class TestChatEndpointWithToolCalls:
    """Integration: verify chat endpoint handles tool calls end-to-end."""

    @pytest.fixture(autouse=True)
    def _clear_chat_history(self):
        import genai_service.chat as chat_mod

        chat_mod.chat_history.clear()
        yield
        chat_mod.chat_history.clear()

    @pytest.fixture
    def app(self):
        from fastapi import FastAPI

        from genai_service.chat import router

        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    async def client(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    @patch("genai_service.chat.get_openai_client")
    @patch("genai_service.chat.get_http_client")
    async def test_chat_with_tool_call_returns_final_response(
        self, mock_get_http, mock_get_openai, client
    ):
        """When OpenAI returns tool_calls, chat should dispatch them and return final text."""
        # First response: tool call
        tc = MagicMock()
        tc.id = "call_1"
        tc.function.name = "listOwners"
        tc.function.arguments = "{}"

        tool_msg = MagicMock()
        tool_msg.content = None
        tool_msg.tool_calls = [tc]
        tool_msg.role = "assistant"
        tool_msg.model_dump.return_value = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": "call_1", "type": "function", "function": {"name": "listOwners", "arguments": "{}"}},
            ],
        }

        first_response = MagicMock()
        first_response.choices = [MagicMock(message=tool_msg)]

        # Second response: final text
        final_msg = MagicMock()
        final_msg.content = "Here are the owners: George"
        final_msg.tool_calls = None

        second_response = MagicMock()
        second_response.choices = [MagicMock(message=final_msg)]

        mock_openai = AsyncMock()
        mock_openai.chat.completions.create = AsyncMock(side_effect=[first_response, second_response])
        mock_get_openai.return_value = mock_openai

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http_response = MagicMock()
        mock_http_response.json.return_value = [{"id": 1, "firstName": "George"}]
        mock_http_response.raise_for_status = MagicMock()
        mock_http.get = AsyncMock(return_value=mock_http_response)
        mock_get_http.return_value = mock_http

        response = await client.post("/chatclient", json="List owners")
        assert response.status_code == 200
        assert response.text == "Here are the owners: George"

    @patch("genai_service.chat.get_openai_client")
    @patch("genai_service.chat.get_http_client")
    async def test_chat_stores_final_reply_in_history(
        self, mock_get_http, mock_get_openai, client
    ):
        """After tool calls resolve, the final assistant reply should be in chat_history."""
        import genai_service.chat as chat_mod

        # Tool call response
        tc = MagicMock()
        tc.id = "call_1"
        tc.function.name = "listOwners"
        tc.function.arguments = "{}"

        tool_msg = MagicMock()
        tool_msg.content = None
        tool_msg.tool_calls = [tc]
        tool_msg.role = "assistant"
        tool_msg.model_dump.return_value = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": "call_1", "type": "function", "function": {"name": "listOwners", "arguments": "{}"}},
            ],
        }
        first_response = MagicMock()
        first_response.choices = [MagicMock(message=tool_msg)]

        final_msg = MagicMock()
        final_msg.content = "Owners listed."
        final_msg.tool_calls = None
        second_response = MagicMock()
        second_response.choices = [MagicMock(message=final_msg)]

        mock_openai = AsyncMock()
        mock_openai.chat.completions.create = AsyncMock(side_effect=[first_response, second_response])
        mock_get_openai.return_value = mock_openai

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http_response = MagicMock()
        mock_http_response.json.return_value = []
        mock_http_response.raise_for_status = MagicMock()
        mock_http.get = AsyncMock(return_value=mock_http_response)
        mock_get_http.return_value = mock_http

        await client.post("/chatclient", json="List owners")

        assert any(m["role"] == "assistant" and m["content"] == "Owners listed." for m in chat_mod.chat_history)
