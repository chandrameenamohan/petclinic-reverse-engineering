"""Tests for POST /owners — create owner with validation."""

import pytest


@pytest.mark.asyncio
async def test_create_owner_returns_201(customers_client):
    """POST /owners with valid data returns 201 Created with the owner."""
    payload = {
        "firstName": "Test",
        "lastName": "User",
        "address": "123 Test St.",
        "city": "TestCity",
        "telephone": "1234567890",
    }
    response = await customers_client.post("/owners", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["firstName"] == "Test"
    assert data["lastName"] == "User"
    assert data["address"] == "123 Test St."
    assert data["city"] == "TestCity"
    assert data["telephone"] == "1234567890"
    assert data["id"] is not None
    assert data["pets"] == []


@pytest.mark.asyncio
async def test_create_owner_persists_in_db(customers_client):
    """Created owner should be retrievable via GET /owners."""
    payload = {
        "firstName": "Persist",
        "lastName": "Check",
        "address": "456 Persist Ave.",
        "city": "PersistCity",
        "telephone": "9876543210",
    }
    create_resp = await customers_client.post("/owners", json=payload)
    assert create_resp.status_code == 201
    owner_id = create_resp.json()["id"]

    list_resp = await customers_client.get("/owners")
    assert list_resp.status_code == 200
    owners = list_resp.json()
    assert any(o["id"] == owner_id and o["firstName"] == "Persist" for o in owners)


@pytest.mark.asyncio
async def test_create_owner_missing_first_name(customers_client):
    """POST /owners with missing firstName returns 422."""
    payload = {
        "lastName": "User",
        "address": "123 Test St.",
        "city": "TestCity",
        "telephone": "1234567890",
    }
    response = await customers_client.post("/owners", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_owner_blank_first_name(customers_client):
    """POST /owners with blank firstName returns 422."""
    payload = {
        "firstName": "",
        "lastName": "User",
        "address": "123 Test St.",
        "city": "TestCity",
        "telephone": "1234567890",
    }
    response = await customers_client.post("/owners", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_owner_missing_last_name(customers_client):
    """POST /owners with missing lastName returns 422."""
    payload = {
        "firstName": "Test",
        "address": "123 Test St.",
        "city": "TestCity",
        "telephone": "1234567890",
    }
    response = await customers_client.post("/owners", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_owner_missing_address(customers_client):
    """POST /owners with missing address returns 422."""
    payload = {
        "firstName": "Test",
        "lastName": "User",
        "city": "TestCity",
        "telephone": "1234567890",
    }
    response = await customers_client.post("/owners", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_owner_missing_city(customers_client):
    """POST /owners with missing city returns 422."""
    payload = {
        "firstName": "Test",
        "lastName": "User",
        "address": "123 Test St.",
        "telephone": "1234567890",
    }
    response = await customers_client.post("/owners", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_owner_missing_telephone(customers_client):
    """POST /owners with missing telephone returns 422."""
    payload = {
        "firstName": "Test",
        "lastName": "User",
        "address": "123 Test St.",
        "city": "TestCity",
    }
    response = await customers_client.post("/owners", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_owner_telephone_non_digits(customers_client):
    """POST /owners with non-digit telephone returns 422."""
    payload = {
        "firstName": "Test",
        "lastName": "User",
        "address": "123 Test St.",
        "city": "TestCity",
        "telephone": "abc123",
    }
    response = await customers_client.post("/owners", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_owner_telephone_too_long(customers_client):
    """POST /owners with telephone > 12 digits returns 422."""
    payload = {
        "firstName": "Test",
        "lastName": "User",
        "address": "123 Test St.",
        "city": "TestCity",
        "telephone": "1234567890123",  # 13 digits
    }
    response = await customers_client.post("/owners", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_owner_alongside_existing(seeded_customers_client):
    """Creating an owner alongside seeded data should work and appear in list."""
    payload = {
        "firstName": "New",
        "lastName": "Owner",
        "address": "789 New St.",
        "city": "NewCity",
        "telephone": "5551234567",
    }
    create_resp = await seeded_customers_client.post("/owners", json=payload)
    assert create_resp.status_code == 201

    list_resp = await seeded_customers_client.get("/owners")
    owners = list_resp.json()
    # Should have seeded owners + the new one
    assert len(owners) >= 3
    new_owner = next(o for o in owners if o["firstName"] == "New")
    assert new_owner["lastName"] == "Owner"
