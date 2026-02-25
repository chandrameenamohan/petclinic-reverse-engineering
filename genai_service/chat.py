"""GenAI chat endpoint — POST /chatclient.

Accepts a JSON string body (user query), calls OpenAI gpt-4o-mini,
and returns the LLM response as plain text.  Maintains in-memory chat
history (last 10 messages) for conversational context.

When the LLM returns tool calls, dispatches them via the tool handler
and loops until a final text response is produced.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Body
from fastapi.responses import PlainTextResponse
from loguru import logger
from openai import AsyncOpenAI

from genai_service.tool_handler import handle_tool_calls
from genai_service.tools import TOOL_DEFINITIONS

router = APIRouter()

FALLBACK_MESSAGE = "Chat is currently unavailable. Please try again later."

SYSTEM_PROMPT = (
    "You are a friendly AI assistant designed to help with the management of a veterinarian pet clinic "
    "called Spring Petclinic. Your job is to answer questions about and to perform actions on the user's "
    "behalf, mainly around veterinarians, owners, owners' pets and owners' visits.\n"
    "You are required to answer an a professional manner. If you don't know the answer, politely tell "
    "the user you don't know the answer, then ask the user a followup question to try and clarify the "
    "question they are asking.\n"
    "If you do know the answer, provide the answer but do not provide any additional followup questions.\n"
    "When dealing with vets, if the user is unsure about the returned results, explain that there may be "
    "additional data that was not returned.\n"
    "Only if the user is asking about the total number of all vets, answer that there are a lot and ask "
    "for some additional criteria.\n"
    "For owners, pets or visits - provide the correct data."
)

# In-memory chat history: list of {"role": "user"|"assistant", "content": "..."}
chat_history: list[dict[str, str]] = []

_MAX_HISTORY_MESSAGES = 10

# Module-level client instances (lazy-initialized via getters for testability)
_openai_client: AsyncOpenAI | None = None
_http_client: httpx.AsyncClient | None = None


def get_openai_client() -> AsyncOpenAI:
    """Return the shared AsyncOpenAI client, creating it on first call."""
    global _openai_client  # noqa: PLW0603
    if _openai_client is None:
        _openai_client = AsyncOpenAI()
    return _openai_client


def get_http_client() -> httpx.AsyncClient:
    """Return the shared httpx client for backend service calls."""
    global _http_client  # noqa: PLW0603
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=10.0)
    return _http_client


@router.post("/chatclient", response_class=PlainTextResponse)
async def chat(query: str = Body(..., media_type="application/json")) -> PlainTextResponse:  # noqa: B008
    """Accept a user query as a JSON string and return an LLM response as plain text."""
    try:
        openai_client = get_openai_client()

        # Append user message to history
        chat_history.append({"role": "user", "content": query})

        # Build messages: system prompt + last N history messages
        recent_history = chat_history[-_MAX_HISTORY_MESSAGES:]
        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *recent_history,
        ]

        logger.debug("GenAI chat request: {}", query)

        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.7,
            messages=messages,  # type: ignore[arg-type]
            tools=TOOL_DEFINITIONS,  # type: ignore[arg-type]
        )

        message = response.choices[0].message

        # Handle tool calls if present
        if message.tool_calls:
            http_client = get_http_client()
            message = await handle_tool_calls(
                openai_client=openai_client,
                http_client=http_client,
                message=message,
                messages=messages,  # type: ignore[arg-type]
            )

        assistant_reply = message.content or ""
        logger.debug("GenAI chat response: {}", assistant_reply)

        # Store assistant reply in history
        chat_history.append({"role": "assistant", "content": assistant_reply})

        return PlainTextResponse(content=assistant_reply)

    except Exception:
        logger.exception("GenAI chat error")
        return PlainTextResponse(content=FALLBACK_MESSAGE)
