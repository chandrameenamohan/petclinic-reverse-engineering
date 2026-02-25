"""Tests for GET /petTypes endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_pet_types_returns_all_sorted_alphabetically(
    seeded_customers_client: AsyncClient,
) -> None:
    """GET /petTypes returns all 6 pet types sorted alphabetically by name."""
    response = await seeded_customers_client.get("/petTypes")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 6
    names = [pt["name"] for pt in data]
    assert names == ["bird", "cat", "dog", "hamster", "lizard", "snake"]


@pytest.mark.asyncio
async def test_get_pet_types_schema(
    seeded_customers_client: AsyncClient,
) -> None:
    """Each pet type has id and name fields."""
    response = await seeded_customers_client.get("/petTypes")

    data = response.json()
    for pet_type in data:
        assert "id" in pet_type
        assert "name" in pet_type
        assert isinstance(pet_type["id"], int)
        assert isinstance(pet_type["name"], str)


@pytest.mark.asyncio
async def test_get_pet_types_empty_db(
    customers_client: AsyncClient,
) -> None:
    """GET /petTypes on empty DB returns empty list."""
    response = await customers_client.get("/petTypes")

    assert response.status_code == 200
    assert response.json() == []
