"""Integration tests for visits service routes."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@pytest.fixture
async def visits_app(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> FastAPI:
    """Create a FastAPI app with visits router and DB dependency override."""
    from visits_service.routes import get_db, router

    app = FastAPI()
    app.include_router(router)

    async def _override_get_db() -> AsyncSession:  # type: ignore[misc]
        async with async_session_factory() as session:
            try:
                yield session  # type: ignore[misc]
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    return app


@pytest.fixture
async def visits_client(visits_app: FastAPI) -> AsyncClient:  # type: ignore[misc]
    """Async HTTP client for the visits service."""
    transport = ASGITransport(app=visits_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client  # type: ignore[misc]


class TestCreateVisit:
    """POST /owners/*/pets/{petId}/visits"""

    async def test_create_visit_with_date(self, visits_client: AsyncClient) -> None:
        """Create a visit with explicit date — returns 201 with visit data."""
        resp = await visits_client.post(
            "/owners/1/pets/7/visits",
            json={"date": "2023-01-15", "description": "Annual checkup"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] is not None
        assert data["date"] == "2023-01-15"
        assert data["description"] == "Annual checkup"
        assert data["petId"] == 7

    async def test_create_visit_date_defaults_today(self, visits_client: AsyncClient) -> None:
        """When date is omitted, it defaults to today."""
        resp = await visits_client.post(
            "/owners/1/pets/7/visits",
            json={"description": "Walk-in visit"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["date"] == date.today().isoformat()
        assert data["petId"] == 7

    async def test_create_visit_petid_from_path_overrides_body(self, visits_client: AsyncClient) -> None:
        """petId from path overrides any petId in the request body."""
        resp = await visits_client.post(
            "/owners/1/pets/7/visits",
            json={"date": "2023-06-01", "description": "Override test", "petId": 999},
        )
        assert resp.status_code == 201
        data = resp.json()
        # Path petId=7 overrides body petId=999
        assert data["petId"] == 7

    async def test_create_visit_description_optional(self, visits_client: AsyncClient) -> None:
        """Description can be omitted (nullable)."""
        resp = await visits_client.post(
            "/owners/1/pets/7/visits",
            json={"date": "2023-01-15"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["description"] is None

    async def test_create_visit_description_max_length(self, visits_client: AsyncClient) -> None:
        """Description max 8192 chars — longer should fail validation."""
        resp = await visits_client.post(
            "/owners/1/pets/7/visits",
            json={"description": "x" * 8193},
        )
        assert resp.status_code == 422

    async def test_create_visit_petid_min_1(self, visits_client: AsyncClient) -> None:
        """petId path param must be >= 1."""
        resp = await visits_client.post(
            "/owners/1/pets/0/visits",
            json={"description": "bad pet id"},
        )
        assert resp.status_code == 422

    async def test_create_visit_persists(self, visits_client: AsyncClient) -> None:
        """Visit is actually persisted — create then verify via a second create with different data."""
        resp1 = await visits_client.post(
            "/owners/1/pets/7/visits",
            json={"date": "2023-01-15", "description": "First visit"},
        )
        resp2 = await visits_client.post(
            "/owners/1/pets/7/visits",
            json={"date": "2023-02-15", "description": "Second visit"},
        )
        assert resp1.status_code == 201
        assert resp2.status_code == 201
        # IDs should be auto-incremented
        assert resp2.json()["id"] > resp1.json()["id"]


class TestGetVisitsForPet:
    """GET /owners/*/pets/{petId}/visits — list visits for a single pet."""

    async def test_returns_empty_list_when_no_visits(self, visits_client: AsyncClient) -> None:
        """Returns 200 with empty array when pet has no visits."""
        resp = await visits_client.get("/owners/1/pets/99/visits")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_returns_visits_for_pet(self, visits_client: AsyncClient) -> None:
        """Returns all visits for the given petId."""
        # Create two visits for pet 7
        await visits_client.post(
            "/owners/1/pets/7/visits",
            json={"date": "2013-01-01", "description": "rabies shot"},
        )
        await visits_client.post(
            "/owners/1/pets/7/visits",
            json={"date": "2013-01-02", "description": "neutering"},
        )
        # Create a visit for pet 8 (should not appear)
        await visits_client.post(
            "/owners/1/pets/8/visits",
            json={"date": "2013-01-03", "description": "vaccination"},
        )

        resp = await visits_client.get("/owners/1/pets/7/visits")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert all(v["petId"] == 7 for v in data)
        descriptions = {v["description"] for v in data}
        assert descriptions == {"rabies shot", "neutering"}

    async def test_response_schema(self, visits_client: AsyncClient) -> None:
        """Each visit has id, date, description, petId keys."""
        await visits_client.post(
            "/owners/1/pets/7/visits",
            json={"date": "2023-05-01", "description": "checkup"},
        )
        resp = await visits_client.get("/owners/1/pets/7/visits")
        assert resp.status_code == 200
        visit = resp.json()[0]
        assert set(visit.keys()) == {"id", "date", "description", "petId"}

    async def test_petid_min_1(self, visits_client: AsyncClient) -> None:
        """petId path param must be >= 1."""
        resp = await visits_client.get("/owners/1/pets/0/visits")
        assert resp.status_code == 422


class TestBatchVisitQuery:
    """GET /pets/visits?petId=7,8 — batch visit query with {items: [...]} wrapper."""

    async def test_returns_visits_for_multiple_pets(self, visits_client: AsyncClient) -> None:
        """Batch query returns visits for all specified pet IDs."""
        await visits_client.post(
            "/owners/1/pets/7/visits",
            json={"date": "2013-01-01", "description": "rabies shot"},
        )
        await visits_client.post(
            "/owners/1/pets/8/visits",
            json={"date": "2013-01-02", "description": "vaccination"},
        )
        # Pet 9 visit should NOT appear
        await visits_client.post(
            "/owners/1/pets/9/visits",
            json={"date": "2013-01-03", "description": "checkup"},
        )

        resp = await visits_client.get("/pets/visits", params={"petId": "7,8"})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) == 2
        pet_ids = {v["petId"] for v in data["items"]}
        assert pet_ids == {7, 8}

    async def test_returns_empty_items_when_no_matches(self, visits_client: AsyncClient) -> None:
        """Returns {items: []} when no visits match the given pet IDs."""
        resp = await visits_client.get("/pets/visits", params={"petId": "999"})
        assert resp.status_code == 200
        data = resp.json()
        assert data == {"items": []}

    async def test_single_pet_id(self, visits_client: AsyncClient) -> None:
        """Works with a single pet ID (no comma)."""
        await visits_client.post(
            "/owners/1/pets/7/visits",
            json={"date": "2023-05-01", "description": "annual"},
        )
        resp = await visits_client.get("/pets/visits", params={"petId": "7"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["petId"] == 7

    async def test_response_schema(self, visits_client: AsyncClient) -> None:
        """Each item in the response has id, date, description, petId keys."""
        await visits_client.post(
            "/owners/1/pets/7/visits",
            json={"date": "2023-05-01", "description": "checkup"},
        )
        resp = await visits_client.get("/pets/visits", params={"petId": "7"})
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert set(item.keys()) == {"id", "date", "description", "petId"}

    async def test_multiple_visits_per_pet(self, visits_client: AsyncClient) -> None:
        """Returns all visits when a pet has multiple visits."""
        await visits_client.post(
            "/owners/1/pets/7/visits",
            json={"date": "2013-01-01", "description": "rabies shot"},
        )
        await visits_client.post(
            "/owners/1/pets/7/visits",
            json={"date": "2013-01-02", "description": "follow-up"},
        )
        resp = await visits_client.get("/pets/visits", params={"petId": "7"})
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 2
