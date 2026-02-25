"""Gateway reverse proxy — routes requests to backend services with StripPrefix=2.

Maps ``/api/{service}/{path}`` to the corresponding backend service URL,
stripping the first two path segments (``/api/{service}``) before forwarding.

Route map:
  /api/customer/** → customers-service :8081
  /api/vet/**      → vets-service      :8083
  /api/visit/**    → visits-service    :8082
  /api/genai/**    → genai-service     :8084
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
from fastapi import APIRouter, Request, Response
from loguru import logger
from pybreaker import CircuitBreakerError
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_result,
    retry_never,
    stop_after_attempt,
)

from api_gateway.circuit_breaker import call_breaker_async, get_breakers
from api_gateway.fallback import FALLBACK_MESSAGE

if TYPE_CHECKING:
    from shared.config import BaseServiceSettings

# Service prefix → backend base URL.
# Defaults match local dev ports; call configure_proxy() to override.
ROUTE_MAP: dict[str, str] = {
    "customer": "http://localhost:8081",
    "vet": "http://localhost:8083",
    "visit": "http://localhost:8082",
    "genai": "http://localhost:8084",
}

# Hop-by-hop headers that must not be forwarded through a proxy.
_HOP_BY_HOP = frozenset({
    "connection",
    "content-length",
    "host",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
})

router = APIRouter()


def configure_proxy(settings: BaseServiceSettings) -> None:
    """Update the route map from service settings."""
    ROUTE_MAP["customer"] = settings.customers_service_url
    ROUTE_MAP["vet"] = settings.vets_service_url
    ROUTE_MAP["visit"] = settings.visits_service_url
    ROUTE_MAP["genai"] = settings.genai_service_url


@router.api_route(
    "/api/{service}/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
)
async def proxy(service: str, path: str, request: Request) -> Response:
    """Reverse-proxy handler with StripPrefix=2.

    Strips ``/api/{service}`` and forwards the remaining path to the
    matching backend service.
    """
    target_base = ROUTE_MAP.get(service)
    if target_base is None:
        return Response(status_code=404, content="Unknown service")

    url = f"{target_base}/{path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"

    body = await request.body()
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in _HOP_BY_HOP
    }

    breakers = get_breakers(service)

    async def _make_request() -> httpx.Response:
        async with httpx.AsyncClient() as client:
            return await client.request(
                method=request.method,
                url=url,
                content=body,
                headers=headers,
                timeout=10.0,
            )

    async def _forward() -> httpx.Response:
        """Forward request through circuit breaker chain."""
        if len(breakers) == 1:
            return await call_breaker_async(breakers[0], _make_request)

        async def _inner() -> httpx.Response:
            return await call_breaker_async(breakers[1], _make_request)

        return await call_breaker_async(breakers[0], _inner)

    # Retry policy: POST + 503 → 1 retry (2 total attempts).
    retry_condition = (
        retry_if_result(lambda resp: resp.status_code == 503)
        if request.method == "POST"
        else retry_never
    )

    def _return_last_result(retry_state: RetryCallState) -> httpx.Response:
        """Return the last response when retries are exhausted (e.g. repeated 503)."""
        result: httpx.Response = retry_state.outcome.result()  # type: ignore[union-attr]
        return result

    try:
        backend_resp = await AsyncRetrying(
            stop=stop_after_attempt(2),
            retry=retry_condition,
            retry_error_callback=_return_last_result,
        ).wraps(_forward)()
    except CircuitBreakerError:
        return Response(
            status_code=503,
            content=FALLBACK_MESSAGE,
            media_type="text/plain",
        )
    except httpx.HTTPError as exc:
        logger.error("Proxy error for {}: {}", url, exc)
        return Response(status_code=502, content="Bad Gateway")

    # Filter hop-by-hop headers from backend response.
    resp_headers = {
        k: v
        for k, v in backend_resp.headers.items()
        if k.lower() not in _HOP_BY_HOP
    }

    return Response(
        content=backend_resp.content,
        status_code=backend_resp.status_code,
        headers=resp_headers,
    )
