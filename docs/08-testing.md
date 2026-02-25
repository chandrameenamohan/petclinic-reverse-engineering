# 08 - Testing Specification

## Overview

This document defines the test strategy for the Python rewrite of the Spring Petclinic Microservices. It maps the existing Java test patterns to Python equivalents and defines comprehensive test coverage requirements for achieving feature parity.

---

## Current Java Test Inventory

### Test Files

| Service | Test File | Type | What It Tests |
|---|---|---|---|
| api-gateway | `ApiGatewayControllerTest` | WebFluxTest | Owner details endpoint with visit merging + circuit breaker fallback |
| api-gateway | `VisitsServiceClientIntegrationTest` | Integration (MockWebServer) | WebClient call to visits-service |
| api-gateway | `ApiGatewayApplicationTests` | SpringBootTest | Application context loads |
| api-gateway | `CircuitBreakerConfiguration` | Test config | Provides Resilience4J beans for tests |
| customers-service | `PetResourceTest` | WebMvcTest | GET pet endpoint with mocked repository |
| vets-service | `VetResourceTest` | WebMvcTest | GET vets endpoint with mocked repository |
| visits-service | `VisitResourceTest` | WebMvcTest | GET visits by pet IDs with mocked repository |
| config-server | `PetclinicConfigServerApplicationTests` | SpringBootTest | Application context loads |
| discovery-server | `DiscoveryServerApplicationTests` | SpringBootTest | Application context loads |

### Java Test Patterns Used

#### 1. @WebMvcTest (Slice Test)
Used by: `PetResourceTest`, `VetResourceTest`, `VisitResourceTest`

Tests a single controller in isolation. Spring loads only the web layer (controller, serialization, validation) and mocks all dependencies.

```java
@WebMvcTest(PetResource.class)
@ActiveProfiles("test")
class PetResourceTest {
    @Autowired MockMvc mvc;
    @MockitoBean PetRepository petRepository;
    @MockitoBean OwnerRepository ownerRepository;

    @Test
    void shouldGetAPetInJSonFormat() throws Exception {
        Pet pet = setupPet();
        given(petRepository.findById(2)).willReturn(Optional.of(pet));

        mvc.perform(get("/owners/2/pets/2").accept(MediaType.APPLICATION_JSON))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.id").value(2))
            .andExpect(jsonPath("$.name").value("Basil"))
            .andExpect(jsonPath("$.type.id").value(6));
    }
}
```

#### 2. @WebFluxTest (Reactive Slice Test)
Used by: `ApiGatewayControllerTest`

Tests a reactive controller with `WebTestClient`. Mocks service clients and tests both happy path and circuit breaker fallback.

```java
@WebFluxTest(controllers = ApiGatewayController.class)
@Import({ReactiveResilience4JAutoConfiguration.class, CircuitBreakerConfiguration.class})
class ApiGatewayControllerTest {
    @MockitoBean CustomersServiceClient customersServiceClient;
    @MockitoBean VisitsServiceClient visitsServiceClient;
    @Autowired WebTestClient client;

    @Test
    void getOwnerDetails_withAvailableVisitsService() {
        // Mock service clients, verify merged response
    }

    @Test
    void getOwnerDetails_withServiceError() {
        // Mock visits service to throw ConnectException
        // Verify circuit breaker returns empty visits (fallback)
    }
}
```

#### 3. MockWebServer (Integration Test)
Used by: `VisitsServiceClientIntegrationTest`

Tests actual HTTP client behavior against a mock HTTP server.

```java
class VisitsServiceClientIntegrationTest {
    private MockWebServer server;

    @BeforeEach
    void setUp() {
        server = new MockWebServer();
        visitsServiceClient = new VisitsServiceClient(WebClient.builder());
        visitsServiceClient.setHostname(server.url("/").toString());
    }

    @Test
    void getVisitsForPets_withAvailableVisitsService() {
        // Enqueue mock response, call client, assert result
    }
}
```

#### 4. @SpringBootTest (Context Load Test)
Used by: `ApiGatewayApplicationTests`, `PetclinicConfigServerApplicationTests`, `DiscoveryServerApplicationTests`

Smoke tests that verify the full application context loads without errors.

---

## Python Test Strategy

### Technology Stack

| Concern | Python Tool | Maps From |
|---|---|---|
| Test framework | `pytest` | JUnit 5 |
| Assertions | `pytest` built-in / `assert` | JUnit assertions |
| HTTP test client | `httpx.AsyncClient` + FastAPI `TestClient` | MockMvc / WebTestClient |
| Mocking | `unittest.mock` / `pytest-mock` | Mockito / @MockitoBean |
| Async testing | `pytest-asyncio` | Reactor test |
| Mock HTTP server | `respx` or `pytest-httpx` | MockWebServer |
| Test database | SQLite in-memory / `pytest` fixtures | H2 in-memory |
| Coverage | `pytest-cov` | JaCoCo |
| JSON path assertions | Direct dict access or `jsonpath-ng` | JsonPath |

### Test Directory Structure

```
tests/
  conftest.py                    # Shared fixtures (test client, DB, mock data)
  unit/
    customers_service/
      test_owner_resource.py     # Owner endpoint unit tests
      test_pet_resource.py       # Pet endpoint unit tests
    vets_service/
      test_vet_resource.py       # Vet endpoint unit tests
    visits_service/
      test_visit_resource.py     # Visit endpoint unit tests
    api_gateway/
      test_gateway_controller.py # Gateway aggregation tests
    genai_service/
      test_chat_client.py        # Chat endpoint tests
      test_tools.py              # Tool function tests
  integration/
    test_visits_client.py        # HTTP client integration tests
    test_database.py             # Repository integration tests
    test_service_discovery.py    # Service registry tests
  e2e/
    test_owner_workflow.py       # Full owner CRUD workflow
    test_visit_workflow.py       # Full visit creation workflow
    test_vet_listing.py          # Vet listing E2E
    test_chat_workflow.py        # Chat interaction E2E
```

---

## Test Data Fixtures

### From customers-service data.sql

```python
# tests/conftest.py
import pytest
from datetime import date

@pytest.fixture
def pet_types():
    return [
        {"id": 1, "name": "cat"},
        {"id": 2, "name": "dog"},
        {"id": 3, "name": "lizard"},
        {"id": 4, "name": "snake"},
        {"id": 5, "name": "bird"},
        {"id": 6, "name": "hamster"},
    ]

@pytest.fixture
def sample_owners():
    return [
        {"id": 1, "first_name": "George", "last_name": "Franklin",
         "address": "110 W. Liberty St.", "city": "Madison", "telephone": "6085551023"},
        {"id": 2, "first_name": "Betty", "last_name": "Davis",
         "address": "638 Cardinal Ave.", "city": "Sun Prairie", "telephone": "6085551749"},
        {"id": 3, "first_name": "Eduardo", "last_name": "Rodriquez",
         "address": "2693 Commerce St.", "city": "McFarland", "telephone": "6085558763"},
        {"id": 4, "first_name": "Harold", "last_name": "Davis",
         "address": "563 Friendly St.", "city": "Windsor", "telephone": "6085553198"},
        {"id": 5, "first_name": "Peter", "last_name": "McTavish",
         "address": "2387 S. Fair Way", "city": "Madison", "telephone": "6085552765"},
        {"id": 6, "first_name": "Jean", "last_name": "Coleman",
         "address": "105 N. Lake St.", "city": "Monona", "telephone": "6085552654"},
        {"id": 7, "first_name": "Jeff", "last_name": "Black",
         "address": "1450 Oak Blvd.", "city": "Monona", "telephone": "6085555387"},
        {"id": 8, "first_name": "Maria", "last_name": "Escobito",
         "address": "345 Maple St.", "city": "Madison", "telephone": "6085557683"},
        {"id": 9, "first_name": "David", "last_name": "Schroeder",
         "address": "2749 Blackhawk Trail", "city": "Madison", "telephone": "6085559435"},
        {"id": 10, "first_name": "Carlos", "last_name": "Estaban",
         "address": "2335 Independence La.", "city": "Waunakee", "telephone": "6085555487"},
    ]

@pytest.fixture
def sample_pets():
    return [
        {"id": 1, "name": "Leo", "birth_date": "2010-09-07", "type_id": 1, "owner_id": 1},
        {"id": 2, "name": "Basil", "birth_date": "2012-08-06", "type_id": 6, "owner_id": 2},
        {"id": 3, "name": "Rosy", "birth_date": "2011-04-17", "type_id": 2, "owner_id": 3},
        {"id": 4, "name": "Jewel", "birth_date": "2010-03-07", "type_id": 2, "owner_id": 3},
        {"id": 5, "name": "Iggy", "birth_date": "2010-11-30", "type_id": 3, "owner_id": 4},
        {"id": 6, "name": "George", "birth_date": "2010-01-20", "type_id": 4, "owner_id": 5},
        {"id": 7, "name": "Samantha", "birth_date": "2012-09-04", "type_id": 1, "owner_id": 6},
        {"id": 8, "name": "Max", "birth_date": "2012-09-04", "type_id": 1, "owner_id": 6},
        {"id": 9, "name": "Lucky", "birth_date": "2011-08-06", "type_id": 5, "owner_id": 7},
        {"id": 10, "name": "Mulligan", "birth_date": "2007-02-24", "type_id": 2, "owner_id": 8},
        {"id": 11, "name": "Freddy", "birth_date": "2010-03-09", "type_id": 5, "owner_id": 9},
        {"id": 12, "name": "Lucky", "birth_date": "2010-06-24", "type_id": 2, "owner_id": 10},
        {"id": 13, "name": "Sly", "birth_date": "2012-06-08", "type_id": 1, "owner_id": 10},
    ]
```

### From vets-service data.sql

```python
@pytest.fixture
def sample_vets():
    return [
        {"id": 1, "first_name": "James", "last_name": "Carter", "specialties": []},
        {"id": 2, "first_name": "Helen", "last_name": "Leary",
         "specialties": [{"id": 1, "name": "radiology"}]},
        {"id": 3, "first_name": "Linda", "last_name": "Douglas",
         "specialties": [{"id": 2, "name": "surgery"}, {"id": 3, "name": "dentistry"}]},
        {"id": 4, "first_name": "Rafael", "last_name": "Ortega",
         "specialties": [{"id": 2, "name": "surgery"}]},
        {"id": 5, "first_name": "Henry", "last_name": "Stevens",
         "specialties": [{"id": 1, "name": "radiology"}]},
        {"id": 6, "first_name": "Sharon", "last_name": "Jenkins", "specialties": []},
    ]

@pytest.fixture
def sample_specialties():
    return [
        {"id": 1, "name": "radiology"},
        {"id": 2, "name": "surgery"},
        {"id": 3, "name": "dentistry"},
    ]
```

### From visits-service data.sql

```python
@pytest.fixture
def sample_visits():
    return [
        {"id": 1, "pet_id": 7, "date": "2013-01-01", "description": "rabies shot"},
        {"id": 2, "pet_id": 8, "date": "2013-01-02", "description": "rabies shot"},
        {"id": 3, "pet_id": 8, "date": "2013-01-03", "description": "neutered"},
        {"id": 4, "pet_id": 7, "date": "2013-01-04", "description": "spayed"},
    ]
```

### Database Fixture

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def db_engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture
def db_session(db_engine):
    """Create a database session for testing."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()

@pytest.fixture
def seeded_db(db_session, sample_owners, sample_pets, sample_vets, sample_visits):
    """Seed the test database with sample data."""
    for owner_data in sample_owners:
        owner = Owner(**owner_data)
        db_session.add(owner)
    # ... add pets, vets, visits
    db_session.commit()
    return db_session
```

### FastAPI Test Client Fixture

```python
import pytest
from httpx import AsyncClient, ASGITransport
from customers_service.main import app

@pytest.fixture
async def client():
    """Async test client for FastAPI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

---

## Unit Tests

### Customers Service - Owner Endpoints

```python
# tests/unit/customers_service/test_owner_resource.py
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

@pytest.mark.asyncio
async def test_get_all_owners(client, sample_owners):
    """Verify GET /owners returns all owners."""
    with patch("customers_service.routes.owner_repo.find_all",
               new_callable=AsyncMock, return_value=sample_owners):
        response = await client.get("/owners")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10
        assert data[0]["firstName"] == "George"
        assert data[0]["lastName"] == "Franklin"


@pytest.mark.asyncio
async def test_get_owner_by_id(client):
    """Verify GET /owners/{id} returns a specific owner."""
    owner = {
        "id": 1, "firstName": "George", "lastName": "Franklin",
        "address": "110 W. Liberty St.", "city": "Madison",
        "telephone": "6085551023", "pets": []
    }
    with patch("customers_service.routes.owner_repo.find_by_id",
               new_callable=AsyncMock, return_value=owner):
        response = await client.get("/owners/1")
        assert response.status_code == 200
        data = response.json()
        assert data["firstName"] == "George"


@pytest.mark.asyncio
async def test_create_owner(client):
    """Verify POST /owners creates a new owner."""
    new_owner = {
        "firstName": "Test", "lastName": "User",
        "address": "123 Test St.", "city": "TestCity",
        "telephone": "1234567890"
    }
    created = {**new_owner, "id": 11, "pets": []}
    with patch("customers_service.routes.owner_repo.save",
               new_callable=AsyncMock, return_value=created):
        response = await client.post("/owners", json=new_owner)
        assert response.status_code == 201
        assert response.json()["id"] == 11


@pytest.mark.asyncio
async def test_update_owner(client):
    """Verify PUT /owners/{id} updates an existing owner."""
    updated = {
        "firstName": "George", "lastName": "Franklin-Updated",
        "address": "110 W. Liberty St.", "city": "Madison",
        "telephone": "6085551023"
    }
    with patch("customers_service.routes.owner_repo.save",
               new_callable=AsyncMock, return_value={**updated, "id": 1}):
        response = await client.put("/owners/1", json=updated)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_owner_not_found(client):
    """Verify GET /owners/{id} returns 404 for non-existent owner."""
    with patch("customers_service.routes.owner_repo.find_by_id",
               new_callable=AsyncMock, return_value=None):
        response = await client.get("/owners/999")
        assert response.status_code == 404
```

### Customers Service - Pet Endpoints

```python
# tests/unit/customers_service/test_pet_resource.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_get_pet_json_format(client):
    """Equivalent of Java PetResourceTest.shouldGetAPetInJSonFormat."""
    pet = {
        "id": 2, "name": "Basil", "birthDate": "2012-08-06",
        "type": {"id": 6, "name": "hamster"}, "visits": []
    }
    with patch("customers_service.routes.pet_repo.find_by_id",
               new_callable=AsyncMock, return_value=pet):
        response = await client.get("/owners/2/pets/2")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert data["id"] == 2
        assert data["name"] == "Basil"
        assert data["type"]["id"] == 6


@pytest.mark.asyncio
async def test_get_pet_types(client, pet_types):
    """Verify GET /petTypes returns all pet types."""
    with patch("customers_service.routes.pet_type_repo.find_all",
               new_callable=AsyncMock, return_value=pet_types):
        response = await client.get("/petTypes")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 6
        assert data[0]["name"] == "cat"


@pytest.mark.asyncio
async def test_create_pet(client):
    """Verify POST /owners/{id}/pets creates a new pet."""
    pet_request = {
        "name": "Rex", "birthDate": "2020-01-15", "typeId": 2
    }
    with patch("customers_service.routes.owner_repo.find_by_id",
               new_callable=AsyncMock, return_value={"id": 1}):
        with patch("customers_service.routes.pet_repo.save",
                   new_callable=AsyncMock, return_value={"id": 14, **pet_request}):
            response = await client.post("/owners/1/pets", json=pet_request)
            assert response.status_code == 201
```

### Vets Service

```python
# tests/unit/vets_service/test_vet_resource.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_get_list_of_vets(client):
    """Equivalent of Java VetResourceTest.shouldGetAListOfVets."""
    vets = [{"id": 1, "firstName": "James", "lastName": "Carter", "specialties": []}]
    with patch("vets_service.routes.vet_repo.find_all",
               new_callable=AsyncMock, return_value=vets):
        response = await client.get("/vets")
        assert response.status_code == 200
        data = response.json()
        assert data[0]["id"] == 1


@pytest.mark.asyncio
async def test_get_vets_with_specialties(client, sample_vets):
    """Verify vets include their specialties."""
    with patch("vets_service.routes.vet_repo.find_all",
               new_callable=AsyncMock, return_value=sample_vets):
        response = await client.get("/vets")
        assert response.status_code == 200
        data = response.json()
        # Helen Leary has radiology
        helen = next(v for v in data if v["firstName"] == "Helen")
        assert len(helen["specialties"]) == 1
        assert helen["specialties"][0]["name"] == "radiology"
        # Linda Douglas has surgery + dentistry
        linda = next(v for v in data if v["firstName"] == "Linda")
        assert len(linda["specialties"]) == 2
```

### Visits Service

```python
# tests/unit/visits_service/test_visit_resource.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_fetch_visits_by_pet_ids(client):
    """Equivalent of Java VisitResourceTest.shouldFetchVisits."""
    visits = [
        {"id": 1, "petId": 111, "date": "2013-01-01", "description": "checkup"},
        {"id": 2, "petId": 222, "date": "2013-01-02", "description": "vaccination"},
        {"id": 3, "petId": 222, "date": "2013-01-03", "description": "surgery"},
    ]
    with patch("visits_service.routes.visit_repo.find_by_pet_id_in",
               new_callable=AsyncMock, return_value=visits):
        response = await client.get("/pets/visits?petId=111,222")
        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["id"] == 1
        assert data["items"][1]["id"] == 2
        assert data["items"][2]["id"] == 3
        assert data["items"][0]["petId"] == 111
        assert data["items"][1]["petId"] == 222
        assert data["items"][2]["petId"] == 222


@pytest.mark.asyncio
async def test_create_visit(client):
    """Verify POST /owners/{oid}/pets/{pid}/visits creates a visit."""
    visit_data = {"date": "2024-01-15", "description": "Annual checkup"}
    with patch("visits_service.routes.visit_repo.save",
               new_callable=AsyncMock, return_value={"id": 5, "petId": 7, **visit_data}):
        response = await client.post("/owners/6/pets/7/visits", json=visit_data)
        assert response.status_code == 201
```

### API Gateway - Aggregation Controller

```python
# tests/unit/api_gateway/test_gateway_controller.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_get_owner_details_with_visits(client):
    """Equivalent of ApiGatewayControllerTest.getOwnerDetails_withAvailableVisitsService."""
    owner = {
        "id": 1, "firstName": "George", "lastName": "Franklin",
        "pets": [{"id": 20, "name": "Garfield", "visits": []}]
    }
    visits = {
        "items": [{"id": 300, "petId": 20, "date": None, "description": "First visit"}]
    }

    with patch("api_gateway.routes.customers_client.get_owner",
               new_callable=AsyncMock, return_value=owner):
        with patch("api_gateway.routes.visits_client.get_visits_for_pets",
                   new_callable=AsyncMock, return_value=visits):
            response = await client.get("/api/gateway/owners/1")
            assert response.status_code == 200
            data = response.json()
            assert data["pets"][0]["name"] == "Garfield"
            assert data["pets"][0]["visits"][0]["description"] == "First visit"


@pytest.mark.asyncio
async def test_get_owner_details_with_service_error(client):
    """Equivalent of ApiGatewayControllerTest.getOwnerDetails_withServiceError.
    Tests circuit breaker fallback: visits-service failure returns empty visits."""
    owner = {
        "id": 1, "firstName": "George", "lastName": "Franklin",
        "pets": [{"id": 20, "name": "Garfield", "visits": []}]
    }

    with patch("api_gateway.routes.customers_client.get_owner",
               new_callable=AsyncMock, return_value=owner):
        with patch("api_gateway.routes.visits_client.get_visits_for_pets",
                   new_callable=AsyncMock, side_effect=ConnectionError("Simulate error")):
            response = await client.get("/api/gateway/owners/1")
            assert response.status_code == 200
            data = response.json()
            assert data["pets"][0]["name"] == "Garfield"
            assert data["pets"][0]["visits"] == []  # Fallback: empty visits
```

### GenAI Service

```python
# tests/unit/genai_service/test_chat_client.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_chat_returns_response(client):
    """Verify POST /chatclient returns LLM response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(
        content="Here are the owners...", tool_calls=None
    ))]

    with patch("genai_service.chat.openai_client.chat.completions.create",
               return_value=mock_response):
        response = await client.post("/chatclient", json="List all owners")
        assert response.status_code == 200
        assert "owners" in response.text.lower()


@pytest.mark.asyncio
async def test_chat_error_returns_fallback(client):
    """Verify chat endpoint returns fallback on error."""
    with patch("genai_service.chat.openai_client.chat.completions.create",
               side_effect=Exception("API error")):
        response = await client.post("/chatclient", json="Hello")
        assert response.status_code == 200
        assert response.text == "Chat is currently unavailable. Please try again later."


# tests/unit/genai_service/test_tools.py
@pytest.mark.asyncio
async def test_list_owners_tool(sample_owners):
    """Verify listOwners tool returns all owners from customers-service."""
    with patch("genai_service.tool_handler.httpx.AsyncClient") as mock_client:
        mock_resp = AsyncMock()
        mock_resp.json.return_value = sample_owners
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)

        result = await dispatch_tool("listOwners", {})
        assert len(result) == 10


@pytest.mark.asyncio
async def test_add_owner_tool():
    """Verify addOwnerToPetclinic tool creates an owner via customers-service."""
    owner_request = {
        "firstName": "Jane", "lastName": "Doe",
        "address": "123 Main St", "city": "Springfield", "telephone": "5551234567"
    }
    created_owner = {**owner_request, "id": 11, "pets": []}

    with patch("genai_service.tool_handler.httpx.AsyncClient") as mock_client:
        mock_resp = AsyncMock()
        mock_resp.json.return_value = created_owner
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)

        result = await dispatch_tool("addOwnerToPetclinic", owner_request)
        assert result["id"] == 11
```

---

## Integration Tests

### HTTP Client Integration (MockWebServer Equivalent)

```python
# tests/integration/test_visits_client.py
import pytest
import respx
from httpx import Response
from visits_service.client import VisitsServiceClient

@pytest.mark.asyncio
async def test_get_visits_for_pets():
    """Equivalent of VisitsServiceClientIntegrationTest."""
    client = VisitsServiceClient(base_url="http://visits-service")

    mock_response = {
        "items": [
            {"id": 5, "date": "2018-11-15", "description": "test visit", "petId": 1}
        ]
    }

    with respx.mock:
        respx.get("http://visits-service/pets/visits", params={"petId": "1"}).mock(
            return_value=Response(200, json=mock_response)
        )

        visits = await client.get_visits_for_pets([1])
        assert len(visits["items"]) == 1
        assert visits["items"][0]["petId"] == 1
        assert visits["items"][0]["description"] == "test visit"
```

### Database Integration

```python
# tests/integration/test_database.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.mark.asyncio
async def test_owner_repository_find_all(seeded_db):
    """Verify owner repository returns all seeded owners."""
    owners = await owner_repo.find_all(seeded_db)
    assert len(owners) == 10


@pytest.mark.asyncio
async def test_owner_repository_find_by_id(seeded_db):
    """Verify owner repository finds by ID."""
    owner = await owner_repo.find_by_id(seeded_db, 1)
    assert owner is not None
    assert owner.first_name == "George"
    assert owner.last_name == "Franklin"


@pytest.mark.asyncio
async def test_pet_repository_with_owner(seeded_db):
    """Verify pet belongs to correct owner."""
    pet = await pet_repo.find_by_id(seeded_db, 1)
    assert pet.name == "Leo"
    assert pet.owner_id == 1


@pytest.mark.asyncio
async def test_visit_repository_find_by_pet_ids(seeded_db):
    """Verify visits can be queried by multiple pet IDs."""
    visits = await visit_repo.find_by_pet_id_in(seeded_db, [7, 8])
    assert len(visits) == 4
    pet_ids = {v.pet_id for v in visits}
    assert pet_ids == {7, 8}
```

---

## End-to-End Tests

### Owner Workflow

```python
# tests/e2e/test_owner_workflow.py
import pytest

@pytest.mark.asyncio
async def test_full_owner_lifecycle(e2e_client):
    """Test complete owner CRUD workflow across services."""
    # 1. Create owner
    new_owner = {
        "firstName": "E2E", "lastName": "TestOwner",
        "address": "999 Test Blvd.", "city": "TestCity",
        "telephone": "1234567890"
    }
    response = await e2e_client.post("/api/customer/owners", json=new_owner)
    assert response.status_code == 201
    owner_id = response.json()["id"]

    # 2. Verify owner exists in list
    response = await e2e_client.get("/api/customer/owners")
    assert response.status_code == 200
    owners = response.json()
    assert any(o["id"] == owner_id for o in owners)

    # 3. Get owner details
    response = await e2e_client.get(f"/api/customer/owners/{owner_id}")
    assert response.status_code == 200
    assert response.json()["firstName"] == "E2E"

    # 4. Update owner
    updated = {**new_owner, "lastName": "UpdatedOwner"}
    response = await e2e_client.put(f"/api/customer/owners/{owner_id}", json=updated)
    assert response.status_code == 200

    # 5. Verify update
    response = await e2e_client.get(f"/api/customer/owners/{owner_id}")
    assert response.json()["lastName"] == "UpdatedOwner"

    # 6. Add pet to owner
    pet = {"name": "TestPet", "birthDate": "2023-01-01", "typeId": 1}
    response = await e2e_client.post(
        f"/api/customer/owners/{owner_id}/pets", json=pet
    )
    assert response.status_code == 201
    pet_id = response.json()["id"]

    # 7. Add visit to pet
    visit = {"date": "2024-06-15", "description": "E2E test visit"}
    response = await e2e_client.post(
        f"/api/visit/owners/{owner_id}/pets/{pet_id}/visits", json=visit
    )
    assert response.status_code == 201

    # 8. Verify through gateway aggregation
    response = await e2e_client.get(f"/api/gateway/owners/{owner_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["pets"]) >= 1
    pet_data = next(p for p in data["pets"] if p["id"] == pet_id)
    assert len(pet_data["visits"]) >= 1
    assert pet_data["visits"][0]["description"] == "E2E test visit"
```

### Vet Listing

```python
# tests/e2e/test_vet_listing.py
import pytest

@pytest.mark.asyncio
async def test_list_vets_with_specialties(e2e_client):
    """Verify vets endpoint returns vets with their specialties."""
    response = await e2e_client.get("/api/vet/vets")
    assert response.status_code == 200
    vets = response.json()
    assert len(vets) >= 6

    # Verify specific vet data
    james = next(v for v in vets if v["firstName"] == "James")
    assert james["lastName"] == "Carter"
    assert len(james["specialties"]) == 0

    linda = next(v for v in vets if v["firstName"] == "Linda")
    specialty_names = {s["name"] for s in linda["specialties"]}
    assert specialty_names == {"surgery", "dentistry"}
```

---

## Application Context / Smoke Tests

```python
# tests/unit/test_app_startup.py
import pytest

@pytest.mark.asyncio
async def test_customers_service_starts():
    """Equivalent of context load test - verify app starts without errors."""
    from customers_service.main import app
    assert app is not None

@pytest.mark.asyncio
async def test_vets_service_starts():
    from vets_service.main import app
    assert app is not None

@pytest.mark.asyncio
async def test_visits_service_starts():
    from visits_service.main import app
    assert app is not None

@pytest.mark.asyncio
async def test_api_gateway_starts():
    from api_gateway.main import app
    assert app is not None
```

---

## pytest Configuration

```ini
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "unit: Unit tests with mocked dependencies",
    "integration: Integration tests with real DB or HTTP",
    "e2e: End-to-end tests across services",
]

[tool.pytest.ini_options.filterwarnings]
ignore = "DeprecationWarning"
```

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/ -m unit

# Integration tests
pytest tests/integration/ -m integration

# E2E tests (requires all services running)
pytest tests/e2e/ -m e2e

# With coverage
pytest --cov=customers_service --cov=vets_service --cov=visits_service \
       --cov=api_gateway --cov=genai_service --cov-report=html

# Specific service
pytest tests/unit/customers_service/

# Verbose with output
pytest -v -s tests/unit/
```

---

## Acceptance Criteria for Feature Parity

### Customers Service
- [ ] GET /owners returns all owners with pets
- [ ] GET /owners/{id} returns single owner with pets
- [ ] POST /owners creates new owner with validation (firstName, lastName, address, city, telephone required)
- [ ] PUT /owners/{id} updates existing owner
- [ ] GET /owners/{id}/pets/{petId} returns pet details
- [ ] POST /owners/{id}/pets creates new pet for owner
- [ ] PUT /owners/{id}/pets/{petId} updates existing pet
- [ ] GET /petTypes returns all 6 pet types
- [ ] Owner not found returns 404
- [ ] Validation errors return 400 with field-level error messages

### Vets Service
- [ ] GET /vets returns all vets with specialties
- [ ] Vets with no specialties return empty specialties array
- [ ] Vets with multiple specialties return all of them

### Visits Service
- [ ] GET /pets/visits?petId=1,2,3 returns visits for specified pet IDs
- [ ] POST /owners/{oid}/pets/{pid}/visits creates new visit
- [ ] Visit response includes id, petId, date, description
- [ ] Response format wraps visits in `{"items": [...]}` wrapper

### API Gateway
- [ ] GET /api/gateway/owners/{id} returns owner with merged visit data
- [ ] Visit data is merged into the correct pet's visits array
- [ ] If visits-service is down, owner is returned with empty visits (circuit breaker)
- [ ] All proxy routes work: /api/customer/**, /api/vet/**, /api/visit/**
- [ ] Static frontend files are served correctly

### GenAI Service
- [ ] POST /chatclient accepts string body and returns LLM response
- [ ] System prompt is included in every request
- [ ] Chat memory maintains last 10 messages of context
- [ ] listOwners tool is callable and returns owner data
- [ ] addOwnerToPetclinic tool creates owners through customers-service
- [ ] listVets tool performs vector similarity search
- [ ] addPetToOwner tool creates pets through customers-service
- [ ] Error in LLM call returns fallback message
- [ ] Vet vector store is loaded on startup

### Frontend
- [ ] Welcome page renders
- [ ] Owner list loads and displays all owners
- [ ] Owner list search filter works
- [ ] Owner detail page shows owner info, pets, and visits
- [ ] Owner create form validates and creates owner
- [ ] Owner edit form pre-populates and updates owner
- [ ] Pet create form shows owner name, validates, and creates pet
- [ ] Pet edit form pre-populates and updates pet
- [ ] Visit form defaults to today's date and creates visit
- [ ] Vet list displays all vets with specialties
- [ ] Chat widget sends/receives messages
- [ ] Chat history persists across page navigation

### Cross-Cutting
- [ ] All services register with service discovery
- [ ] Health endpoints available at /actuator/health
- [ ] Services can be configured via external config server
- [ ] Distributed tracing headers are propagated between services
