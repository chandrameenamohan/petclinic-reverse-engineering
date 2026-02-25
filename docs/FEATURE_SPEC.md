# Spring Petclinic Microservices — Feature Specification

> **Source**: Spring Petclinic Microservices (Java/Spring Boot)
> **Tested against**: `localhost:8080` (Docker Compose full stack)
> **Date**: 2026-02-25

---

## Table of Contents

1. [Owner Management](#1-owner-management)
2. [Pet Management](#2-pet-management)
3. [Veterinarian Management](#3-veterinarian-management)
4. [Visit Management](#4-visit-management)
5. [GenAI Chat Service](#5-genai-chat-service)
6. [Frontend UI Pages](#6-frontend-ui-pages)
7. [Infrastructure & Observability](#7-infrastructure--observability)
8. [Seed Data](#8-seed-data)

---

## 1. Owner Management

### 1.1 List All Owners

| | |
|---|---|
| **Endpoint** | `GET /api/customer/owners` |
| **Status** | 200 |
| **Response** | JSON array of owner objects |

**Owner fields**: `id` (int), `firstName` (string), `lastName` (string), `address` (string), `city` (string), `telephone` (string), `pets` (array)

**Pet fields** (nested): `id` (int), `name` (string), `birthDate` (YYYY-MM-DD), `type` ({`id`, `name`})

**Sorting**: By `id` ascending. Pets within owner by `id` ascending.

**Note**: The `lastName` query parameter (`?lastName=X`) is accepted but **ignored** — always returns all owners. Filtering is client-side only (via AngularJS in the frontend).

### 1.2 Get Single Owner

| | |
|---|---|
| **Endpoint** | `GET /api/customer/owners/{id}` |
| **Status** | 200 (even for non-existent) |
| **Response** | Single owner object, or `null` |

- Non-existent owner (e.g., ID=999) returns **200 with `null` body** (not 404).

### 1.3 Create Owner

| | |
|---|---|
| **Endpoint** | `POST /api/customer/owners` |
| **Content-Type** | `application/json` |
| **Status** | 201 Created |

**Required fields** (all 5): `firstName`, `lastName`, `address`, `city`, `telephone`

**Validation**:
- All fields must be non-empty strings (min 1 char)
- `telephone` must be 1-12 digits only
- Missing/invalid fields return 422 with detailed errors

**Response**: Created owner object with assigned `id` and empty `pets` array.

### 1.4 Update Owner

| | |
|---|---|
| **Endpoint** | `PUT /api/customer/owners/{id}` |
| **Status** | 204 No Content |

- Full replacement (all fields required, no PATCH support)
- Non-existent owner returns 404 `{"detail":"Owner not found"}`
- Same validation as create

### 1.5 BFF Owner Details (Aggregation)

| | |
|---|---|
| **Endpoint** | `GET /api/gateway/owners/{id}` |
| **Status** | 200 |

- Merges data from customers-service + visits-service
- Same as direct owner API, but each pet includes a `visits` array
- **Visit fields**: `id` (int), `petId` (int), `date` (YYYY-MM-DD), `description` (string)
- Non-existent owner returns 200 with `null` (same as direct API)

---

## 2. Pet Management

### 2.1 List Pet Types

| | |
|---|---|
| **Endpoint** | `GET /api/customer/petTypes` |
| **Status** | 200 |

**Response**: Array of `{id, name}` sorted alphabetically by name.

**6 types**: bird, cat, dog, hamster, lizard, snake

Pet types are **read-only** — no single-type lookup, no create/update/delete.

### 2.2 Get Single Pet

| | |
|---|---|
| **Endpoint** | `GET /api/customer/owners/{ownerId}/pets/{petId}` |
| **Status** | 200 |

**Response fields**: `id`, `name`, `owner` (string — full name), `birthDate`, `type` ({`id`, `name`})

**Notable**:
- The `owner` field is a **string** (e.g., "George Franklin"), not an object
- The `ownerId` in the URL path is **ignored** — pet is fetched by petId only
- Non-existent pet returns 404 `{"detail":"Pet not found"}`
- No direct `/api/customer/pets/{id}` endpoint (404)

### 2.3 Create Pet

| | |
|---|---|
| **Endpoint** | `POST /api/customer/owners/{ownerId}/pets` |
| **Content-Type** | `application/json` |
| **Status** | 201 Created |

**Request format**: `{"name": "...", "birthDate": "YYYY-MM-DD", "typeId": 2}`
- Uses flat `typeId` (NOT nested type object)
- Only `typeId` is strictly required; `name` and `birthDate` can be null
- Non-existent owner returns 404

**Response**: Created pet with resolved `type` object (no `owner` field in response).

### 2.4 Update Pet

| | |
|---|---|
| **Endpoint** | `PUT /api/customer/owners/{ownerId}/pets/{petId}` |
| **Status** | 204 No Content |

**Request format**: `{"id": 1, "name": "...", "birthDate": "...", "typeId": 1}`
- **Must include `id` in body** — without it returns 400 `{"detail":"Pet id required in body"}`
- The body `id` determines which pet is updated (URL petId is ignored)
- `typeId` is required; `name` and `birthDate` optional
- No DELETE endpoint (405)

---

## 3. Veterinarian Management

### 3.1 List All Vets

| | |
|---|---|
| **Endpoint** | `GET /api/vet/vets` |
| **Status** | 200 |

**Response**: JSON array of vet objects (bare array, no wrapper).

**Vet fields**: `id` (int), `firstName` (string), `lastName` (string), `specialties` (array of `{id, name}`)

**Sorting**: By `id` ascending.

**6 vets seeded**:
| ID | Name | Specialties |
|----|------|-------------|
| 1 | James Carter | (none) |
| 2 | Helen Leary | radiology |
| 3 | Linda Douglas | dentistry, surgery |
| 4 | Rafael Ortega | surgery |
| 5 | Henry Stevens | radiology |
| 6 | Sharon Jenkins | (none) |

**Vets are read-only**: No single vet lookup, no CRUD operations. Only `GET /vets` (list all).

---

## 4. Visit Management

### 4.1 Get Visits for a Pet

| | |
|---|---|
| **Endpoint** | `GET /api/visit/owners/{ownerId}/pets/{petId}/visits` |
| **Status** | 200 |

**Response**: Bare JSON array of visit objects.

**Visit fields**: `id` (int), `petId` (int), `date` (YYYY-MM-DD), `description` (string, nullable)

**Note**: The `ownerId` in the path is **ignored** — visits are filtered by `petId` only.

### 4.2 Batch Visit Query

| | |
|---|---|
| **Endpoint** | `GET /api/visit/pets/visits?petId=1,2,3` |
| **Status** | 200 |

**Response**: Wrapped in `{"items": [...]}` (unlike single-pet which returns bare array).

- Missing `petId` param returns 422
- Non-existent petIds return `{"items": []}`

### 4.3 Create Visit

| | |
|---|---|
| **Endpoint** | `POST /api/visit/owners/{ownerId}/pets/{petId}/visits` |
| **Content-Type** | `application/json` |
| **Status** | 201 Created |

**Request format**: `{"date": "YYYY-MM-DD", "description": "..."}`
- Very lenient: empty body `{}` succeeds (date defaults to today, description null)
- Only invalid date format causes 422
- `petId` is set from URL path parameter

**Response**: Created visit object with auto-generated `id`.

**No update or delete** endpoints for visits (404).

---

## 5. GenAI Chat Service

### 5.1 Chat Endpoint

| | |
|---|---|
| **Endpoint** | `POST /api/genai/chatclient` |
| **Content-Type** | `application/json` |
| **Status** | 200 |

**Request**: JSON-encoded string (bare quoted string, NOT an object).
```
curl -X POST .../api/genai/chatclient -H "Content-Type: application/json" -d '"Hello"'
```

**Response**: Plain text (`text/plain`). May contain markdown.

**Error handling**: All errors return 200 with `"Chat is currently unavailable. Please try again later."` — the frontend never sees HTTP errors from chat.

### 5.2 LLM Configuration

- **Model**: OpenAI gpt-4o-mini, temperature 0.7
- **System prompt**: Veterinarian clinic assistant persona
- **Memory**: Last 10 messages (in-memory, shared across all users, not session-isolated, lost on restart)

### 5.3 Tool Calling (Function Calling)

4 tools available to the LLM:

| Tool | Action | Backend Call |
|------|--------|-------------|
| `listOwners` | List all owners | `GET customers-service/owners` |
| `addOwnerToPetclinic` | Create owner (firstName, lastName, address, city, telephone) | `POST customers-service/owners` |
| `listVets` | Search vets via vector similarity | ChromaDB search, fallback to `GET vets-service/vets` |
| `addPetToOwner` | Add pet (ownerId, name, birthDate, typeId) | `POST customers-service/owners/{id}/pets` |

**Tool loop**: Up to 10 iterations — LLM can chain multiple tool calls before returning final text.

### 5.4 Vector Store

- **ChromaDB** ephemeral (in-memory)
- Loads vet data on startup from `vectorstore.json` file or fetches from vets-service
- Similarity search: top_k=20 (filtered) or 50 (unfiltered)

### 5.5 Circuit Breaker

- Dual circuit breaker: genaiCircuitBreaker (fail_max=5) + defaultCircuitBreaker (fail_max=50)
- When tripped: returns 503 with fallback message
- Retry: POST + 503 → 1 retry (2 total attempts)

---

## 6. Frontend UI Pages

**Architecture**: AngularJS 1.x SPA with `ui.router`, hash-based routing (`#!/...`)

### 6.1 Welcome Page

| | |
|---|---|
| **Route** | `#!/welcome` (default) |
| **Content** | "Welcome to Petclinic" heading + pets.png image |

Static page, no interactive elements.

### 6.2 Navigation Bar

Dark navbar with Spring logo. 4 links:

| Label | Icon | Route |
|-------|------|-------|
| Home | fa-home | `/` |
| Find Owners | fa-search | `#!/owners` |
| Register Owner | fa-plus | `#!/owners/new` |
| Veterinarians | fa-th-list | `#!/vets` |

Active link highlighted. Responsive with mobile collapse toggle.

### 6.3 Owners List

| | |
|---|---|
| **Route** | `#!/owners` |
| **API** | `GET /api/customer/owners` |

- **Client-side search filter**: Text input filters all columns via AngularJS `| filter` pipe
- **Table columns**: Name (linked to details), Address (hidden on small), City, Telephone, Pets (hidden on xs)
- No server-side search, no pagination — loads all owners at once

### 6.4 Owner Details

| | |
|---|---|
| **Route** | `#!/owners/details/:ownerId` |
| **API** | `GET /api/gateway/owners/:id` (BFF composite) |

- Owner info table: Name, Address, City, Telephone
- Buttons: "Edit Owner", "Add New Pet"
- **Pets and Visits section**: For each pet shows Name (linked to edit), Birth Date (formatted `yyyy MMM dd`), Type
- Visit history table per pet: Visit Date, Description
- Per-pet actions: "Edit Pet", "Add Visit"

### 6.5 Owner Form (Create/Edit)

| | |
|---|---|
| **Create route** | `#!/owners/new` |
| **Edit route** | `#!/owners/:ownerId/edit` |

**Fields**: First name, Last name, Address, City, Telephone (pattern: exactly 12 digits)
- All fields required with inline validation messages
- Create → POST, redirects to owners list
- Edit → PUT, redirects to owner details

### 6.6 Pet Form (Create/Edit)

| | |
|---|---|
| **Create route** | `#!/owners/:ownerId/new-pet` |
| **Edit route** | `#!/owners/:ownerId/pets/:petId` |

**Fields**: Owner (read-only), Name (required), Birth date (date picker, required), Type (dropdown from petTypes API)
- Default type: first in list
- Submit → redirects to owner details

### 6.7 Visit Form

| | |
|---|---|
| **Route** | `#!/owners/:ownerId/pets/:petId/visits` |
| **API** | `GET/POST /api/visit/owners/:ownerId/pets/:petId/visits` |

**Fields**: Date (defaults to today), Description (textarea, required)
- Shows "Previous Visits" table below the form
- Submit → redirects to owner details

### 6.8 Vets List

| | |
|---|---|
| **Route** | `#!/vets` |
| **API** | `GET /api/vet/vets` |

- Striped table: Name, Specialties (space-separated)
- Read-only, no links, no search, no pagination

### 6.9 Chat Widget

- **Always visible** on every page (fixed bottom-right)
- Toggle expand/collapse by clicking "Chat with Us!" header
- WhatsApp-style: green header (#075E54), green user bubbles (#dcf8c6), white bot bubbles
- **Send**: Click "Send" button or press Enter
- **Markdown**: Bot responses rendered via `marked.js`
- **Persistence**: Chat history saved to `localStorage` (survives page refresh)
- **Error fallback**: "Chat is currently unavailable" shown as bot message on fetch failure

### 6.10 Footer

Centered Spring by Pivotal logo image. No links or text.

### 6.11 Error Handling

- Global `HttpErrorHandlingInterceptor` shows browser `alert()` for validation errors
- Expects error format: `{"error": "...", "errors": [{field, defaultMessage}]}`
- Safari cache workaround: `Cache-Control: no-cache` on all requests

---

## 7. Infrastructure & Observability

### 7.1 Service Ports

| Port | Service |
|------|---------|
| 8080 | API Gateway |
| 8081 | Customers Service |
| 8082 | Visits Service |
| 8083 | Vets Service |
| 8084 | GenAI Service |
| 8761 | Discovery (Eureka) |
| 8888 | Config Server |
| 9090 | Admin Server |

### 7.2 Health Endpoints

All services expose `GET /actuator/health` → `{"status":"UP"}`.

Eureka has richer response with `groups: ["liveness", "readiness"]`.

### 7.3 Info Endpoints

All business services expose `GET /actuator/info`:
```json
{"build":{"artifact":"<service-name>","version":"1.0.0"},"git":{"branch":"main","commit":"unknown"}}
```

### 7.4 Prometheus Metrics

- Backend services (8081, 8082, 8083) expose `GET /actuator/prometheus` in Prometheus text format
- Gateway (8080) does **not** expose Prometheus metrics
- Includes Python GC metrics and HTTP request metrics

### 7.5 Admin Dashboard

`GET http://localhost:9090/dashboard` → Aggregated health of all 5 business services:
```json
{"customers-service":{"status":"UP"},"visits-service":{"status":"UP"},"vets-service":{"status":"UP"},"genai-service":{"status":"UP"},"api-gateway":{"status":"UP"}}
```

### 7.6 Gateway Proxy Routes

| Path Prefix | Target Service | Strip Prefix |
|-------------|----------------|-------------|
| `/api/customer/` | `localhost:8081` | 2 segments |
| `/api/visit/` | `localhost:8082` | 2 segments |
| `/api/vet/` | `localhost:8083` | 2 segments |
| `/api/genai/` | `localhost:8084` | 2 segments |

---

## 8. Seed Data

### 8.1 Owners (10)

| ID | Name | City | Telephone | Pets |
|----|------|------|-----------|------|
| 1 | George Franklin | Madison | 6085551023 | Leo (cat) |
| 2 | Betty Davis | Sun Prairie | 6085551749 | Basil (hamster) |
| 3 | Eduardo Rodriquez | McFarland | 6085558763 | Jewel (dog), Rosy (dog) |
| 4 | Harold Davis | Windsor | 6085553198 | Iggy (lizard) |
| 5 | Peter McTavish | Madison | 6085552765 | George (snake) |
| 6 | Jean Coleman | Monona | 6085552654 | Max (cat), Samantha (cat) |
| 7 | Jeff Black | Monona | 6085555387 | Lucky (bird) |
| 8 | Maria Escobito | Madison | 6085557683 | Mulligan (dog) |
| 9 | David Schroeder | Madison | 6085559435 | Freddy (bird) |
| 10 | Carlos Estaban | Waunakee | 6085555487 | Lucky (dog), Sly (cat) |

### 8.2 Pet Types (6)

bird, cat, dog, hamster, lizard, snake

### 8.3 Visits (4)

| ID | Pet | Date | Description |
|----|-----|------|-------------|
| 1 | Samantha (7) | 2013-01-01 | rabies shot |
| 2 | Max (8) | 2013-01-02 | rabies shot |
| 3 | Max (8) | 2013-01-03 | neutered |
| 4 | Samantha (7) | 2013-01-04 | spayed |

### 8.4 Vets (6)

| ID | Name | Specialties |
|----|------|-------------|
| 1 | James Carter | (none) |
| 2 | Helen Leary | radiology |
| 3 | Linda Douglas | dentistry, surgery |
| 4 | Rafael Ortega | surgery |
| 5 | Henry Stevens | radiology |
| 6 | Sharon Jenkins | (none) |

### 8.5 Specialties (3)

radiology, surgery, dentistry
