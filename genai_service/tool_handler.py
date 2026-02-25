"""GenAI tool call handler — dispatches LLM tool calls to backend services.

Implements:
- ``dispatch_tool``: Routes individual tool calls to the correct backend HTTP endpoint
- ``handle_tool_calls``: Loops over tool calls from OpenAI, dispatches them, and
  re-submits results until the LLM produces a final text response.

Backend calls:
- listOwners → GET customers-service/owners
- addOwnerToPetclinic → POST customers-service/owners
- addPetToOwner → POST customers-service/owners/{ownerId}/pets
- listVets → chromadb vector store similarity search (HTTP fallback if store empty)
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import httpx
from loguru import logger

from genai_service.tools import TOOL_DEFINITIONS

if TYPE_CHECKING:
    from openai import AsyncOpenAI
    from openai.types.chat import ChatCompletionMessage

# Configurable service URLs (overridden by settings or tests)
CUSTOMERS_SERVICE_URL = "http://localhost:8081"
VETS_SERVICE_URL = "http://localhost:8083"

# Safety limit to prevent infinite tool-call loops
MAX_TOOL_ITERATIONS = 10


async def dispatch_tool(
    name: str,
    args: dict[str, object],
    http_client: httpx.AsyncClient,
) -> object:
    """Dispatch a single tool call to the appropriate backend service.

    Returns the parsed JSON response, or an error dict on failure.
    """
    try:
        result: Any
        if name == "listOwners":
            resp = await http_client.get(f"{CUSTOMERS_SERVICE_URL}/owners")
            resp.raise_for_status()
            result = resp.json()
            return result

        if name == "addOwnerToPetclinic":
            resp = await http_client.post(f"{CUSTOMERS_SERVICE_URL}/owners", json=args)
            resp.raise_for_status()
            result = resp.json()
            return result

        if name == "addPetToOwner":
            owner_id = args.pop("ownerId")
            resp = await http_client.post(
                f"{CUSTOMERS_SERVICE_URL}/owners/{owner_id}/pets",
                json=args,
            )
            resp.raise_for_status()
            result = resp.json()
            return result

        if name == "listVets":
            # Use vector store similarity search; fall back to HTTP if not initialized
            from genai_service.vector_store import search_vets

            vet_filter = args if args else None
            results = await search_vets(vet_filter)
            if results:
                return results
            # Fallback: direct HTTP call if vector store is empty/not initialized
            resp = await http_client.get(f"{VETS_SERVICE_URL}/vets")
            resp.raise_for_status()
            result = resp.json()
            return result

        return {"error": f"Unknown tool: {name}"}

    except Exception as exc:
        logger.warning("Tool dispatch error for {}: {}", name, exc)
        return {"error": str(exc)}


async def handle_tool_calls(
    *,
    openai_client: AsyncOpenAI,
    http_client: httpx.AsyncClient,
    message: ChatCompletionMessage,
    messages: list[dict[str, object]],
) -> ChatCompletionMessage:
    """Process tool calls from the LLM in a loop until a final text response.

    1. For each tool_call in message.tool_calls, call dispatch_tool
    2. Append assistant message + tool results to messages
    3. Re-submit to OpenAI
    4. Repeat if more tool_calls are returned (up to MAX_TOOL_ITERATIONS)
    """
    current_message = message

    for _iteration in range(MAX_TOOL_ITERATIONS):
        if not current_message.tool_calls:
            break

        # Collect tool results
        tool_result_messages: list[dict[str, object]] = []
        for tool_call in current_message.tool_calls:
            fn = getattr(tool_call, "function", None)
            if fn is None:
                continue
            fn_name: str = fn.name
            fn_args: dict[str, object] = json.loads(fn.arguments)

            logger.debug("Dispatching tool call: {} with args: {}", fn_name, fn_args)
            result = await dispatch_tool(fn_name, fn_args, http_client)

            tool_result_messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

        # Build updated message list: original messages + assistant message + tool results
        updated_messages: list[dict[str, object]] = [
            *messages,
            current_message.model_dump(),
            *tool_result_messages,
        ]

        # Re-submit to OpenAI
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.7,
            messages=updated_messages,  # type: ignore[arg-type]
            tools=TOOL_DEFINITIONS,  # type: ignore[arg-type]
        )

        current_message = response.choices[0].message
        # Update messages for next iteration (if needed)
        messages = updated_messages

    return current_message
