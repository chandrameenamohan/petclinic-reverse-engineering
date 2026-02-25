"""Unit tests for gateway circuit breaker integration."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import httpx
import pytest
import respx
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from httpx import Response as HttpxResponse

from api_gateway.circuit_breaker import default_breaker, genai_breaker
from api_gateway.fallback import FALLBACK_MESSAGE
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


class TestCircuitBreakerConfig:
    """Verify circuit breaker configuration matches spec."""

    def test_default_breaker_fail_max(self) -> None:
        assert default_breaker.fail_max == 50

    def test_default_breaker_reset_timeout(self) -> None:
        assert default_breaker.reset_timeout == 60

    def test_default_breaker_name(self) -> None:
        assert default_breaker.name == "defaultCircuitBreaker"

    def test_genai_breaker_fail_max(self) -> None:
        assert genai_breaker.fail_max == 5

    def test_genai_breaker_reset_timeout(self) -> None:
        assert genai_breaker.reset_timeout == 60

    def test_genai_breaker_name(self) -> None:
        assert genai_breaker.name == "genaiCircuitBreaker"


class TestDefaultBreakerOpen:
    """When default breaker is open, all routes return 503 fallback."""

    @respx.mock
    async def test_customer_route_returns_503(self, client: AsyncClient) -> None:
        default_breaker.open()
        response = await client.get("/api/customer/owners")
        assert response.status_code == 503
        assert response.text == FALLBACK_MESSAGE

    @respx.mock
    async def test_vet_route_returns_503(self, client: AsyncClient) -> None:
        default_breaker.open()
        response = await client.get("/api/vet/vets")
        assert response.status_code == 503
        assert response.text == FALLBACK_MESSAGE

    @respx.mock
    async def test_genai_route_returns_503_when_default_open(
        self, client: AsyncClient
    ) -> None:
        default_breaker.open()
        response = await client.post("/api/genai/chatclient", content='"Hello"')
        assert response.status_code == 503
        assert response.text == FALLBACK_MESSAGE

    async def test_fallback_content_type_is_text_plain(
        self, client: AsyncClient
    ) -> None:
        default_breaker.open()
        response = await client.get("/api/customer/owners")
        assert "text/plain" in response.headers["content-type"]


class TestGenaiBreaker:
    """GenAI breaker only affects genai routes."""

    @respx.mock
    async def test_genai_open_returns_503(self, client: AsyncClient) -> None:
        genai_breaker.open()
        response = await client.post("/api/genai/chatclient", content='"Hello"')
        assert response.status_code == 503
        assert response.text == FALLBACK_MESSAGE

    @respx.mock
    async def test_genai_open_does_not_affect_customer(
        self, client: AsyncClient
    ) -> None:
        genai_breaker.open()
        respx.get("http://localhost:8081/owners").mock(
            return_value=HttpxResponse(200, json=[])
        )
        response = await client.get("/api/customer/owners")
        assert response.status_code == 200

    @respx.mock
    async def test_genai_open_does_not_affect_vet(
        self, client: AsyncClient
    ) -> None:
        genai_breaker.open()
        respx.get("http://localhost:8083/vets").mock(
            return_value=HttpxResponse(200, json=[])
        )
        response = await client.get("/api/vet/vets")
        assert response.status_code == 200


class TestBreakerRecordsFailures:
    """Connection errors increment breaker failure count."""

    @respx.mock
    async def test_connect_error_counts_as_failure(
        self, client: AsyncClient
    ) -> None:
        respx.get("http://localhost:8081/owners").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        response = await client.get("/api/customer/owners")
        assert response.status_code == 502
        assert default_breaker.fail_counter > 0

    @respx.mock
    async def test_success_resets_fail_counter(self, client: AsyncClient) -> None:
        respx.get("http://localhost:8081/owners").mock(
            return_value=HttpxResponse(200, json=[])
        )
        response = await client.get("/api/customer/owners")
        assert response.status_code == 200
        assert default_breaker.fail_counter == 0

    @respx.mock
    async def test_genai_connect_error_counts_on_both_breakers(
        self, client: AsyncClient
    ) -> None:
        respx.post("http://localhost:8084/chatclient").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        response = await client.post("/api/genai/chatclient", content='"Hello"')
        assert response.status_code == 502
        assert default_breaker.fail_counter > 0
        assert genai_breaker.fail_counter > 0


class TestBreakerClosedPassthrough:
    """When breakers are closed, requests pass through normally."""

    @respx.mock
    async def test_customer_request_passes_through(
        self, client: AsyncClient
    ) -> None:
        route = respx.get("http://localhost:8081/owners").mock(
            return_value=HttpxResponse(200, json=[{"id": 1}])
        )
        response = await client.get("/api/customer/owners")
        assert response.status_code == 200
        assert route.called

    @respx.mock
    async def test_genai_request_passes_through(self, client: AsyncClient) -> None:
        route = respx.post("http://localhost:8084/chatclient").mock(
            return_value=HttpxResponse(200, text="Hello!")
        )
        response = await client.post("/api/genai/chatclient", content='"Hello"')
        assert response.status_code == 200
        assert route.called
