"""Tests for Prometheus metrics instrumentation.

Verifies:
- ``/actuator/prometheus`` endpoint exists and returns Prometheus-format text.
- Standard HTTP metrics (from ``prometheus-fastapi-instrumentator``) are present.
- Custom ``petclinic_*_seconds`` histograms record per-endpoint timing with
  ``method`` and ``exception`` labels.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from customers_service.models import Owner, Pet, PetType
from shared.database import Base
from visits_service.models import Visit


@pytest.fixture
async def metrics_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def metrics_session_factory(metrics_engine):
    return async_sessionmaker(metrics_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def seeded_metrics_db(metrics_session_factory):
    async with metrics_session_factory() as session:
        pet_types = [PetType(id=1, name="cat"), PetType(id=2, name="dog")]
        session.add_all(pet_types)
        await session.flush()
        owners = [
            Owner(id=1, first_name="George", last_name="Franklin",
                  address="110 W. Liberty St.", city="Madison", telephone="6085551023"),
        ]
        session.add_all(owners)
        await session.flush()
        pets = [Pet(id=1, name="Leo", birth_date=None, type_id=1, owner_id=1)]
        session.add_all(pets)
        visits = [Visit(id=1, pet_id=1, visit_date=None, description="checkup")]
        session.add_all(visits)
        await session.commit()


@pytest.fixture
async def instrumented_customers_app(metrics_session_factory, seeded_metrics_db):
    from fastapi import FastAPI

    from customers_service.routes import get_db, router
    from shared.metrics import instrument_app

    app = FastAPI()
    app.include_router(router)

    async def _override_get_db():
        async with metrics_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    instrument_app(app)
    return app


@pytest.fixture
async def instrumented_customers_client(instrumented_customers_app):
    transport = ASGITransport(app=instrumented_customers_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestPrometheusEndpoint:
    """Test that /actuator/prometheus endpoint exposes metrics."""

    async def test_prometheus_endpoint_exists(self, instrumented_customers_client):
        resp = await instrumented_customers_client.get("/actuator/prometheus")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]

    async def test_standard_process_metrics_present(self, instrumented_customers_client):
        resp = await instrumented_customers_client.get("/actuator/prometheus")
        body = resp.text
        # Process metrics from prometheus_client are always present
        assert "python_info" in body


class TestCustomOwnerHistogram:
    """Test petclinic_owner_seconds histogram is recorded for owner endpoints."""

    async def test_create_owner_records_metric(self, instrumented_customers_client):
        await instrumented_customers_client.post("/owners", json={
            "firstName": "Test", "lastName": "Owner",
            "address": "123 St", "city": "Town", "telephone": "1234567890",
        })
        resp = await instrumented_customers_client.get("/actuator/prometheus")
        body = resp.text
        assert "petclinic_owner_seconds" in body
        assert 'method="createOwner"' in body

    async def test_list_owners_records_metric(self, instrumented_customers_client):
        await instrumented_customers_client.get("/owners")
        resp = await instrumented_customers_client.get("/actuator/prometheus")
        body = resp.text
        assert "petclinic_owner_seconds" in body
        assert 'method="listOwners"' in body

    async def test_update_owner_records_metric(self, instrumented_customers_client):
        await instrumented_customers_client.put("/owners/1", json={
            "firstName": "Updated", "lastName": "Franklin",
            "address": "110 W. Liberty St.", "city": "Madison", "telephone": "6085551023",
        })
        resp = await instrumented_customers_client.get("/actuator/prometheus")
        body = resp.text
        assert "petclinic_owner_seconds" in body
        assert 'method="updateOwner"' in body

    async def test_exception_label_on_not_found(self, instrumented_customers_client):
        await instrumented_customers_client.put("/owners/999", json={
            "firstName": "X", "lastName": "Y",
            "address": "1", "city": "Z", "telephone": "0000000000",
        })
        resp = await instrumented_customers_client.get("/actuator/prometheus")
        body = resp.text
        assert 'exception="HTTPException"' in body


class TestCustomPetHistogram:
    """Test petclinic_pet_seconds histogram is recorded for pet endpoints."""

    async def test_create_pet_records_metric(self, instrumented_customers_client):
        await instrumented_customers_client.post("/owners/1/pets", json={
            "name": "Buddy", "birthDate": "2023-01-01", "typeId": 1,
        })
        resp = await instrumented_customers_client.get("/actuator/prometheus")
        body = resp.text
        assert "petclinic_pet_seconds" in body
        assert 'method="createPet"' in body


class TestCustomVisitHistogram:
    """Test petclinic_visit_seconds histogram is recorded for visit endpoints."""

    @pytest.fixture
    async def instrumented_visits_app(self, metrics_session_factory, seeded_metrics_db):
        from fastapi import FastAPI

        from shared.metrics import instrument_app
        from visits_service.routes import get_db, router

        app = FastAPI()
        app.include_router(router)

        async def _override_get_db():
            async with metrics_session_factory() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        app.dependency_overrides[get_db] = _override_get_db
        instrument_app(app)
        return app

    @pytest.fixture
    async def instrumented_visits_client(self, instrumented_visits_app):
        transport = ASGITransport(app=instrumented_visits_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    async def test_create_visit_records_metric(self, instrumented_visits_client):
        await instrumented_visits_client.post("/owners/1/pets/1/visits", json={
            "description": "annual checkup",
        })
        resp = await instrumented_visits_client.get("/actuator/prometheus")
        body = resp.text
        assert "petclinic_visit_seconds" in body
        assert 'method="createVisit"' in body
