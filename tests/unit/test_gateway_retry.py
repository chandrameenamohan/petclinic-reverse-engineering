"""Unit tests for gateway retry logic.

Retry policy: POST requests returning 503 are retried once (2 total attempts).
GET and other methods are NOT retried, regardless of status code.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import respx
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from httpx import Response as HttpxResponse

from api_gateway.circuit_breaker import default_breaker, genai_breaker
from api_gateway.proxy import router


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_breakers() -> None:
    """Reset circuit breakers to closed state between tests."""
    default_breaker.close()
    genai_breaker.close()


class TestPostRetryOn503:
    """POST requests returning 503 are retried once."""

    @respx.mock
    async def test_post_503_then_200_returns_200(self, client: AsyncClient) -> None:
        """POST that gets 503 first, then 200 on retry — should succeed."""
        route = respx.post("http://localhost:8081/owners").mock(
            side_effect=[
                HttpxResponse(503, text="Service Unavailable"),
                HttpxResponse(200, json={"id": 1}),
            ]
        )
        response = await client.post(
            "/api/customer/owners", json={"firstName": "George"}
        )
        assert response.status_code == 200
        assert route.call_count == 2

    @respx.mock
    async def test_post_503_twice_returns_503(self, client: AsyncClient) -> None:
        """POST that gets 503 both times — returns 503 after 2 attempts."""
        route = respx.post("http://localhost:8081/owners").mock(
            return_value=HttpxResponse(503, text="Service Unavailable")
        )
        response = await client.post(
            "/api/customer/owners", json={"firstName": "George"}
        )
        assert response.status_code == 503
        assert route.call_count == 2

    @respx.mock
    async def test_genai_post_503_retried(self, client: AsyncClient) -> None:
        """POST to genai service also retried on 503."""
        route = respx.post("http://localhost:8084/chatclient").mock(
            side_effect=[
                HttpxResponse(503, text="Service Unavailable"),
                HttpxResponse(200, text="Hello!"),
            ]
        )
        response = await client.post("/api/genai/chatclient", content='"Hello"')
        assert response.status_code == 200
        assert route.call_count == 2

    @respx.mock
    async def test_visit_post_503_retried(self, client: AsyncClient) -> None:
        """POST to visits service also retried on 503."""
        route = respx.post("http://localhost:8082/owners/1/pets/1/visits").mock(
            side_effect=[
                HttpxResponse(503, text="Service Unavailable"),
                HttpxResponse(201, json={"id": 1}),
            ]
        )
        response = await client.post(
            "/api/visit/owners/1/pets/1/visits",
            json={"description": "checkup"},
        )
        assert response.status_code == 201
        assert route.call_count == 2


class TestNoRetryOnNon503:
    """POST requests returning non-503 status codes are NOT retried."""

    @respx.mock
    async def test_post_404_not_retried(self, client: AsyncClient) -> None:
        route = respx.post("http://localhost:8081/owners").mock(
            return_value=HttpxResponse(404, json={"detail": "Not found"})
        )
        response = await client.post(
            "/api/customer/owners", json={"firstName": "George"}
        )
        assert response.status_code == 404
        assert route.call_count == 1

    @respx.mock
    async def test_post_200_not_retried(self, client: AsyncClient) -> None:
        route = respx.post("http://localhost:8081/owners").mock(
            return_value=HttpxResponse(201, json={"id": 1})
        )
        response = await client.post(
            "/api/customer/owners", json={"firstName": "George"}
        )
        assert response.status_code == 201
        assert route.call_count == 1

    @respx.mock
    async def test_post_500_not_retried(self, client: AsyncClient) -> None:
        route = respx.post("http://localhost:8081/owners").mock(
            return_value=HttpxResponse(500, text="Internal Server Error")
        )
        response = await client.post(
            "/api/customer/owners", json={"firstName": "George"}
        )
        assert response.status_code == 500
        assert route.call_count == 1


class TestNoRetryOnGet:
    """GET requests are NEVER retried, even on 503."""

    @respx.mock
    async def test_get_503_not_retried(self, client: AsyncClient) -> None:
        route = respx.get("http://localhost:8081/owners").mock(
            return_value=HttpxResponse(503, text="Service Unavailable")
        )
        response = await client.get("/api/customer/owners")
        assert response.status_code == 503
        assert route.call_count == 1

    @respx.mock
    async def test_get_200_not_retried(self, client: AsyncClient) -> None:
        route = respx.get("http://localhost:8081/owners").mock(
            return_value=HttpxResponse(200, json=[])
        )
        response = await client.get("/api/customer/owners")
        assert response.status_code == 200
        assert route.call_count == 1


class TestNoRetryOnPut:
    """PUT requests are NEVER retried."""

    @respx.mock
    async def test_put_503_not_retried(self, client: AsyncClient) -> None:
        route = respx.put("http://localhost:8081/owners/1").mock(
            return_value=HttpxResponse(503, text="Service Unavailable")
        )
        response = await client.put(
            "/api/customer/owners/1", json={"firstName": "Updated"}
        )
        assert response.status_code == 503
        assert route.call_count == 1


class TestNoRetryOnDelete:
    """DELETE requests are NEVER retried."""

    @respx.mock
    async def test_delete_503_not_retried(self, client: AsyncClient) -> None:
        route = respx.delete("http://localhost:8081/owners/1").mock(
            return_value=HttpxResponse(503, text="Service Unavailable")
        )
        response = await client.delete("/api/customer/owners/1")
        assert response.status_code == 503
        assert route.call_count == 1
