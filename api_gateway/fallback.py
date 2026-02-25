"""Gateway fallback endpoint — returns 503 when circuit breaker triggers."""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter()

FALLBACK_MESSAGE = "Chat is currently unavailable. Please try again later."


@router.post("/fallback", response_class=PlainTextResponse, status_code=503)
async def fallback() -> PlainTextResponse:
    """Circuit breaker fallback — returns 503 Service Unavailable."""
    return PlainTextResponse(content=FALLBACK_MESSAGE, status_code=503)
