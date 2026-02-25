"""Unit tests for the gateway reverse proxy."""

from collections.abc import AsyncGenerator

import httpx
import pytest
import respx
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from httpx import Response as HttpxResponse

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


class TestProxyRouteMapping:
    """Verify each service prefix maps to the correct backend."""

    @respx.mock
    async def test_customer_route(self, client: AsyncClient) -> None:
        route = respx.get("http://localhost:8081/owners").mock(
            return_value=HttpxResponse(200, json=[{"id": 1}])
        )
        response = await client.get("/api/customer/owners")
        assert response.status_code == 200
        assert route.called

    @respx.mock
    async def test_vet_route(self, client: AsyncClient) -> None:
        route = respx.get("http://localhost:8083/vets").mock(
            return_value=HttpxResponse(200, json=[])
        )
        response = await client.get("/api/vet/vets")
        assert response.status_code == 200
        assert route.called

    @respx.mock
    async def test_visit_route(self, client: AsyncClient) -> None:
        route = respx.post("http://localhost:8082/owners/1/pets/1/visits").mock(
            return_value=HttpxResponse(201, json={"id": 1})
        )
        response = await client.post(
            "/api/visit/owners/1/pets/1/visits",
            json={"description": "checkup"},
        )
        assert response.status_code == 201
        assert route.called

    @respx.mock
    async def test_genai_route(self, client: AsyncClient) -> None:
        route = respx.post("http://localhost:8084/chatclient").mock(
            return_value=HttpxResponse(200, text="Hello!")
        )
        response = await client.post("/api/genai/chatclient", content='"Hello"')
        assert response.status_code == 200
        assert route.called

    async def test_unknown_service_returns_404(self, client: AsyncClient) -> None:
        response = await client.get("/api/unknown/foo")
        assert response.status_code == 404


class TestStripPrefix:
    """Verify StripPrefix=2 strips /api/{service} from forwarded path."""

    @respx.mock
    async def test_strips_two_segments(self, client: AsyncClient) -> None:
        route = respx.get("http://localhost:8081/owners/1/pets").mock(
            return_value=HttpxResponse(200, json=[])
        )
        response = await client.get("/api/customer/owners/1/pets")
        assert response.status_code == 200
        assert route.called

    @respx.mock
    async def test_deep_nested_path(self, client: AsyncClient) -> None:
        route = respx.get("http://localhost:8082/owners/1/pets/2/visits").mock(
            return_value=HttpxResponse(200, json=[])
        )
        response = await client.get("/api/visit/owners/1/pets/2/visits")
        assert response.status_code == 200
        assert route.called


class TestRequestForwarding:
    """Verify request body, query params, and methods are forwarded."""

    @respx.mock
    async def test_forwards_query_params(self, client: AsyncClient) -> None:
        route = respx.get("http://localhost:8082/pets/visits").mock(
            return_value=HttpxResponse(200, json={"items": []})
        )
        response = await client.get("/api/visit/pets/visits?petId=7,8")
        assert response.status_code == 200
        assert route.called
        request_url = str(route.calls[0].request.url)
        assert "petId=" in request_url

    @respx.mock
    async def test_forwards_post_body(self, client: AsyncClient) -> None:
        route = respx.post("http://localhost:8081/owners").mock(
            return_value=HttpxResponse(201, json={"id": 1})
        )
        body = {"firstName": "George", "lastName": "Franklin"}
        response = await client.post("/api/customer/owners", json=body)
        assert response.status_code == 201
        assert route.called
        assert b"George" in route.calls[0].request.content

    @respx.mock
    async def test_forwards_put_method(self, client: AsyncClient) -> None:
        route = respx.put("http://localhost:8081/owners/1").mock(
            return_value=HttpxResponse(204)
        )
        response = await client.put(
            "/api/customer/owners/1", json={"firstName": "Updated"}
        )
        assert response.status_code == 204
        assert route.called

    @respx.mock
    async def test_forwards_delete_method(self, client: AsyncClient) -> None:
        route = respx.delete("http://localhost:8081/owners/1").mock(
            return_value=HttpxResponse(204)
        )
        response = await client.delete("/api/customer/owners/1")
        assert response.status_code == 204
        assert route.called


class TestResponseForwarding:
    """Verify backend responses are forwarded correctly."""

    @respx.mock
    async def test_forwards_error_status(self, client: AsyncClient) -> None:
        respx.get("http://localhost:8081/owners/999").mock(
            return_value=HttpxResponse(404, json={"detail": "Not found"})
        )
        response = await client.get("/api/customer/owners/999")
        assert response.status_code == 404

    @respx.mock
    async def test_forwards_response_body(self, client: AsyncClient) -> None:
        expected = [{"id": 1, "firstName": "George"}]
        respx.get("http://localhost:8081/owners").mock(
            return_value=HttpxResponse(200, json=expected)
        )
        response = await client.get("/api/customer/owners")
        assert response.json() == expected

    @respx.mock
    async def test_backend_connection_error_returns_502(self, client: AsyncClient) -> None:
        respx.get("http://localhost:8081/owners").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        response = await client.get("/api/customer/owners")
        assert response.status_code == 502
