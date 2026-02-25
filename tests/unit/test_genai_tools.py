"""Unit tests for GenAI tool definitions (OpenAI function calling format)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


class TestToolDefinitionsStructure:
    """Verify TOOL_DEFINITIONS matches the OpenAI function calling schema."""

    def test_tool_definitions_is_a_list(self) -> None:
        from genai_service.tools import TOOL_DEFINITIONS

        assert isinstance(TOOL_DEFINITIONS, list)

    def test_tool_definitions_has_four_tools(self) -> None:
        from genai_service.tools import TOOL_DEFINITIONS

        assert len(TOOL_DEFINITIONS) == 4

    def test_all_tools_have_type_function(self) -> None:
        from genai_service.tools import TOOL_DEFINITIONS

        for tool in TOOL_DEFINITIONS:
            assert tool["type"] == "function"

    def test_all_tools_have_function_key_with_name_description_parameters(self) -> None:
        from genai_service.tools import TOOL_DEFINITIONS

        for tool in TOOL_DEFINITIONS:
            fn = tool["function"]
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn

    def test_tool_names(self) -> None:
        from genai_service.tools import TOOL_DEFINITIONS

        names = [t["function"]["name"] for t in TOOL_DEFINITIONS]
        assert "listOwners" in names
        assert "addOwnerToPetclinic" in names
        assert "listVets" in names
        assert "addPetToOwner" in names


class TestListOwnersTool:
    """listOwners: no params, description from spec."""

    def _get_tool(self) -> dict[str, object]:
        from genai_service.tools import TOOL_DEFINITIONS

        return next(t for t in TOOL_DEFINITIONS if t["function"]["name"] == "listOwners")

    def test_description(self) -> None:
        tool = self._get_tool()
        assert "List the owners that the pet clinic has" in tool["function"]["description"]

    def test_no_required_params(self) -> None:
        tool = self._get_tool()
        params = tool["function"]["parameters"]
        assert params["type"] == "object"
        assert params.get("required", []) == []
        assert params.get("properties", {}) == {}


class TestAddOwnerTool:
    """addOwnerToPetclinic: 5 required string fields, description from spec."""

    def _get_tool(self) -> dict[str, object]:
        from genai_service.tools import TOOL_DEFINITIONS

        return next(t for t in TOOL_DEFINITIONS if t["function"]["name"] == "addOwnerToPetclinic")

    def test_description_mentions_first_last_name_address_phone(self) -> None:
        tool = self._get_tool()
        desc = tool["function"]["description"]
        assert "first name" in desc
        assert "last name" in desc
        assert "address" in desc
        assert "10-digit phone number" in desc

    def test_required_fields(self) -> None:
        tool = self._get_tool()
        required = tool["function"]["parameters"]["required"]
        assert set(required) == {"firstName", "lastName", "address", "city", "telephone"}

    def test_all_fields_are_strings(self) -> None:
        tool = self._get_tool()
        props = tool["function"]["parameters"]["properties"]
        for field in ("firstName", "lastName", "address", "city", "telephone"):
            assert props[field]["type"] == "string"


class TestListVetsTool:
    """listVets: optional vet filter, description from spec."""

    def _get_tool(self) -> dict[str, object]:
        from genai_service.tools import TOOL_DEFINITIONS

        return next(t for t in TOOL_DEFINITIONS if t["function"]["name"] == "listVets")

    def test_description(self) -> None:
        tool = self._get_tool()
        assert "veterinarians" in tool["function"]["description"].lower()

    def test_no_required_params(self) -> None:
        tool = self._get_tool()
        params = tool["function"]["parameters"]
        assert params.get("required", []) == []

    def test_has_optional_filter_fields(self) -> None:
        tool = self._get_tool()
        props = tool["function"]["parameters"]["properties"]
        assert "firstName" in props
        assert "lastName" in props
        assert "specialties" in props


class TestAddPetToOwnerTool:
    """addPetToOwner: ownerId, name, birthDate, typeId — all required."""

    def _get_tool(self) -> dict[str, object]:
        from genai_service.tools import TOOL_DEFINITIONS

        return next(t for t in TOOL_DEFINITIONS if t["function"]["name"] == "addPetToOwner")

    def test_description_mentions_pet_type_ids(self) -> None:
        tool = self._get_tool()
        desc = tool["function"]["description"]
        assert "1 = cat" in desc or "1=cat" in desc
        assert "2 = dog" in desc or "2=dog" in desc
        assert "6" in desc  # hamster

    def test_required_fields(self) -> None:
        tool = self._get_tool()
        required = tool["function"]["parameters"]["required"]
        assert set(required) == {"ownerId", "name", "birthDate", "typeId"}

    def test_owner_id_is_integer(self) -> None:
        tool = self._get_tool()
        props = tool["function"]["parameters"]["properties"]
        assert props["ownerId"]["type"] == "integer"

    def test_type_id_is_integer(self) -> None:
        tool = self._get_tool()
        props = tool["function"]["parameters"]["properties"]
        assert props["typeId"]["type"] == "integer"

    def test_name_is_string(self) -> None:
        tool = self._get_tool()
        props = tool["function"]["parameters"]["properties"]
        assert props["name"]["type"] == "string"

    def test_birth_date_is_string(self) -> None:
        tool = self._get_tool()
        props = tool["function"]["parameters"]["properties"]
        assert props["birthDate"]["type"] == "string"

    def test_owner_id_has_description(self) -> None:
        tool = self._get_tool()
        props = tool["function"]["parameters"]["properties"]
        assert "description" in props["ownerId"]


class TestChatEndpointPassesTools:
    """Verify the chat endpoint passes TOOL_DEFINITIONS to OpenAI."""

    @pytest.fixture(autouse=True)
    def _clear_chat_history(self) -> None:  # type: ignore[return]
        import genai_service.chat as chat_mod

        chat_mod.chat_history.clear()
        yield
        chat_mod.chat_history.clear()

    @pytest.fixture
    def mock_openai_response(self) -> MagicMock:
        choice = MagicMock()
        choice.message.content = "Hello!"
        choice.message.tool_calls = None
        response = MagicMock()
        response.choices = [choice]
        return response

    @pytest.fixture
    def app(self) -> object:
        from fastapi import FastAPI

        from genai_service.chat import router

        application = FastAPI()
        application.include_router(router)
        return application

    @pytest.fixture
    async def client(self, app: object) -> AsyncClient:  # type: ignore[misc]
        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c  # type: ignore[misc]

    @patch("genai_service.chat.get_openai_client")
    async def test_chat_passes_tools_to_openai(
        self,
        mock_get_client: AsyncMock,
        client: AsyncClient,
        mock_openai_response: MagicMock,
    ) -> None:
        from genai_service.tools import TOOL_DEFINITIONS

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        mock_get_client.return_value = mock_client

        await client.post("/chatclient", json="List owners")

        call_kwargs = mock_client.chat.completions.create.call_args
        assert "tools" in call_kwargs.kwargs
        assert call_kwargs.kwargs["tools"] == TOOL_DEFINITIONS
