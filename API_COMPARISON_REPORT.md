# API Comparison Report: Python vs Spring Petclinic Microservices

**Generated:** 2026-02-25
**Python capture:** 2026-02-25T04:13-04:16 UTC
**Spring capture:** 2026-02-25 09:54:29 UTC

---

## Summary Scorecard

| # | Endpoint | Verdict |
|---|----------|---------|
| 1 | GET /owners | MATCH |
| 2 | GET /owners/1 | MATCH |
| 3 | GET /owners/999 | MATCH |
| 4 | GET /petTypes | MATCH |
| 5 | GET /owners/1/pets/1 | MATCH |
| 6 | GET /vets | DIFFERENCE - missing `nrOfSpecialties` field in Python |
| 7 | GET /pets/visits?petId=7 | DIFFERENCE - field ordering differs |
| 8 | GET /pets/visits?petId=7,8 (batch) | DIFFERENCE - field ordering differs |
| 9 | GET /owners/6/pets/7/visits | DIFFERENCE - field ordering differs |
| 10 | GET /api/gateway/owners/1 (BFF) | DIFFERENCE - Python includes `type.id`, Spring omits it |
| 11 | GET /api/gateway/owners/6 (BFF) | DIFFERENCE - Python includes `type.id`, Spring omits it |
| 12 | GET /actuator/health | DIFFERENCE - Content-Type header differs |
| 13 | GET /actuator/info | DIFFERENCE - structure and content differ significantly |

**Total: 5 exact matches, 8 with differences (most are minor/cosmetic)**

---

## 1. GET /owners (all owners list)

### Status Code
**[MATCH]** Both return `HTTP 200 OK`

### Content-Type
**[MATCH]** Both return `Content-Type: application/json`

### Response Structure
**[MATCH]** Both return a JSON array of owner objects.

### Field Names
**[MATCH]** Identical: `id`, `firstName`, `lastName`, `address`, `city`, `telephone`, `pets[]` with nested `id`, `name`, `birthDate`, `type.id`, `type.name`

### Owner Order
**[MATCH]** Both return owners sorted by `id` ascending (1 through 10).

### Pet Order Within Owner
**[MATCH]** Both sort pets alphabetically by name within each owner. For example:
- Owner 3: Jewel (id=4) before Rosy (id=3)
- Owner 6: Max (id=8) before Samantha (id=7)
- Owner 10: Lucky (id=12) before Sly (id=13)

### Field Values
**[MATCH]** All 10 owners with all 13 pets have identical data values.

### Sample (Owner 1) -- Python:
```json
{
  "id": 1,
  "firstName": "George",
  "lastName": "Franklin",
  "address": "110 W. Liberty St.",
  "city": "Madison",
  "telephone": "6085551023",
  "pets": [
    {
      "id": 1,
      "name": "Leo",
      "birthDate": "2010-09-07",
      "type": {"id": 1, "name": "cat"}
    }
  ]
}
```

### Sample (Owner 1) -- Spring:
```json
{
  "id": 1,
  "firstName": "George",
  "lastName": "Franklin",
  "address": "110 W. Liberty St.",
  "city": "Madison",
  "telephone": "6085551023",
  "pets": [
    {
      "id": 1,
      "name": "Leo",
      "birthDate": "2010-09-07",
      "type": {
        "id": 1,
        "name": "cat"
      }
    }
  ]
}
```

### Verdict: **MATCH** -- Fully compatible.

---

## 2. GET /owners/1 (single owner)

### Status Code
**[MATCH]** Both return `HTTP 200 OK`

### Content-Type
**[MATCH]** Both return `Content-Type: application/json`

### Response Structure
**[MATCH]** Both return a single owner JSON object (not wrapped in an array).

### Field Names & Values
**[MATCH]** Identical structure and values.

### Python:
```json
{
  "id": 1,
  "firstName": "George",
  "lastName": "Franklin",
  "address": "110 W. Liberty St.",
  "city": "Madison",
  "telephone": "6085551023",
  "pets": [
    {
      "id": 1,
      "name": "Leo",
      "birthDate": "2010-09-07",
      "type": {"id": 1, "name": "cat"}
    }
  ]
}
```

### Spring:
```json
{
  "id": 1,
  "firstName": "George",
  "lastName": "Franklin",
  "address": "110 W. Liberty St.",
  "city": "Madison",
  "telephone": "6085551023",
  "pets": [
    {
      "id": 1,
      "name": "Leo",
      "birthDate": "2010-09-07",
      "type": {
        "id": 1,
        "name": "cat"
      }
    }
  ]
}
```

### Verdict: **MATCH** -- Fully compatible.

---

## 3. GET /owners/999 (non-existent owner)

### Status Code
**[MATCH]** Both return `HTTP 200 OK` (not 404)

### Content-Type
**[MATCH]** Both return `Content-Type: application/json`

### Response Body
**[MATCH]** Both return the literal text `null`

### Python:
```
HTTP/1.1 200 OK
Content-Type: application/json
Body: null
```

### Spring:
```
HTTP/1.1 200 OK
Content-Type: application/json
Body: null
```

### Notes
Both correctly replicate the Java `Optional` behavior of returning HTTP 200 with body `null` for non-existent resources rather than a 404.

### Verdict: **MATCH** -- Fully compatible.

---

## 4. GET /petTypes

### Status Code
**[MATCH]** Both return `HTTP 200 OK`

### Content-Type
**[MATCH]** Both return `Content-Type: application/json`

### Response Structure
**[MATCH]** Both return a JSON array of `{id, name}` objects.

### Sort Order
**[MATCH]** Both sorted alphabetically by `name`: bird, cat, dog, hamster, lizard, snake.

### Field Names & Values
**[MATCH]** Identical.

### Python:
```json
[
  {"id": 5, "name": "bird"},
  {"id": 1, "name": "cat"},
  {"id": 2, "name": "dog"},
  {"id": 6, "name": "hamster"},
  {"id": 3, "name": "lizard"},
  {"id": 4, "name": "snake"}
]
```

### Spring:
```json
[
  {"id": 5, "name": "bird"},
  {"id": 1, "name": "cat"},
  {"id": 2, "name": "dog"},
  {"id": 6, "name": "hamster"},
  {"id": 3, "name": "lizard"},
  {"id": 4, "name": "snake"}
]
```

### Verdict: **MATCH** -- Fully compatible.

---

## 5. GET /owners/1/pets/1 (pet detail)

### Status Code
**[MATCH]** Both return `HTTP 200 OK`

### Content-Type
**[MATCH]** Both return `Content-Type: application/json`

### Response Structure
**[MATCH]** Both return a flat pet object with `owner` as a "firstName lastName" string (not a nested object).

### Field Names & Values
**[MATCH]** Identical: `id`, `name`, `owner`, `birthDate`, `type.id`, `type.name`

### Python:
```json
{
  "id": 1,
  "name": "Leo",
  "owner": "George Franklin",
  "birthDate": "2010-09-07",
  "type": {"id": 1, "name": "cat"}
}
```

### Spring:
```json
{
  "id": 1,
  "name": "Leo",
  "owner": "George Franklin",
  "birthDate": "2010-09-07",
  "type": {
    "id": 1,
    "name": "cat"
  }
}
```

### Verdict: **MATCH** -- Fully compatible.

---

## 6. GET /vets

### Status Code
**[MATCH]** Both return `HTTP 200 OK`

### Content-Type
**[MATCH]** Both return `Content-Type: application/json`

### Response Structure
**[MATCH]** Both return a JSON array of vet objects.

### Field Names
**[DIFFERENCE]**

| Field | Python | Spring |
|-------|--------|--------|
| `id` | Present | Present |
| `firstName` | Present | Present |
| `lastName` | Present | Present |
| `specialties` | Present | Present |
| `nrOfSpecialties` | **MISSING IN PYTHON** | Present |

### Specialties Content
**[MATCH]** Both include `id` and `name` in each specialty object. Both use same ordering (dentistry before surgery for Linda Douglas).

### Python:
```json
[
  {"id": 1, "firstName": "James", "lastName": "Carter", "specialties": []},
  {"id": 2, "firstName": "Helen", "lastName": "Leary", "specialties": [{"id": 1, "name": "radiology"}]},
  {"id": 3, "firstName": "Linda", "lastName": "Douglas", "specialties": [{"id": 3, "name": "dentistry"}, {"id": 2, "name": "surgery"}]},
  {"id": 4, "firstName": "Rafael", "lastName": "Ortega", "specialties": [{"id": 2, "name": "surgery"}]},
  {"id": 5, "firstName": "Henry", "lastName": "Stevens", "specialties": [{"id": 1, "name": "radiology"}]},
  {"id": 6, "firstName": "Sharon", "lastName": "Jenkins", "specialties": []}
]
```

### Spring:
```json
[
  {"id": 1, "firstName": "James", "lastName": "Carter", "specialties": [], "nrOfSpecialties": 0},
  {"id": 2, "firstName": "Helen", "lastName": "Leary", "specialties": [{"id": 1, "name": "radiology"}], "nrOfSpecialties": 1},
  {"id": 3, "firstName": "Linda", "lastName": "Douglas", "specialties": [{"id": 3, "name": "dentistry"}, {"id": 2, "name": "surgery"}], "nrOfSpecialties": 2},
  {"id": 4, "firstName": "Rafael", "lastName": "Ortega", "specialties": [{"id": 2, "name": "surgery"}], "nrOfSpecialties": 1},
  {"id": 5, "firstName": "Henry", "lastName": "Stevens", "specialties": [{"id": 1, "name": "radiology"}], "nrOfSpecialties": 1},
  {"id": 6, "firstName": "Sharon", "lastName": "Jenkins", "specialties": [], "nrOfSpecialties": 0}
]
```

### Verdict: **DIFFERENCE** -- Python is missing the `nrOfSpecialties` computed field that Spring includes on each vet. This is a derived field (length of `specialties` array), but the Spring version serializes it as a JSON property. Consumers relying on this field would break.

---

## 7. GET /pets/visits?petId=7 (single pet visits)

### Status Code
**[MATCH]** Both return `HTTP 200 OK`

### Content-Type
**[MATCH]** Both return `Content-Type: application/json`

### Wrapper Structure
**[MATCH]** Both use `{"items": [...]}` wrapper.

### Visit Data Values
**[MATCH]** Both return the same 2 visits (id=1 rabies shot, id=4 spayed) for petId=7.

### Field Names
**[MATCH]** Both include `id`, `date`, `description`, `petId` in each visit.

### Field Ordering Within Visit Object
**[DIFFERENCE]**

| Python field order | Spring field order |
|---|---|
| `id`, `petId`, `date`, `description` | `id`, `date`, `description`, `petId` |

### Python:
```json
{
  "items": [
    {"id": 1, "petId": 7, "date": "2013-01-01", "description": "rabies shot"},
    {"id": 4, "petId": 7, "date": "2013-01-04", "description": "spayed"}
  ]
}
```

### Spring:
```json
{
  "items": [
    {"id": 1, "date": "2013-01-01", "description": "rabies shot", "petId": 7},
    {"id": 4, "date": "2013-01-04", "description": "spayed", "petId": 7}
  ]
}
```

### Verdict: **MINOR DIFFERENCE** -- JSON key ordering within visit objects differs. Python places `petId` second, Spring places it last. JSON spec says key order is not meaningful, so well-behaved clients should not be affected. Functionally equivalent.

---

## 8. GET /pets/visits?petId=7,8 (batch visits)

### Status Code
**[MATCH]** Both return `HTTP 200 OK`

### Content-Type
**[MATCH]** Both return `Content-Type: application/json`

### Wrapper Structure
**[MATCH]** Both use `{"items": [...]}` wrapper.

### Visit Data Values
**[MATCH]** Both return 4 visits: id=1 (pet7), id=4 (pet7), id=2 (pet8), id=3 (pet8).

### Visit Ordering
**[MATCH]** Both return visits grouped by pet, with pet 7's visits first, then pet 8's. Within each pet, visits are ordered by id.

### Field Ordering Within Visit Object
**[DIFFERENCE]** Same as endpoint #7: Python has `petId` second, Spring has `petId` last.

### Python:
```json
{
  "items": [
    {"id": 1, "petId": 7, "date": "2013-01-01", "description": "rabies shot"},
    {"id": 4, "petId": 7, "date": "2013-01-04", "description": "spayed"},
    {"id": 2, "petId": 8, "date": "2013-01-02", "description": "rabies shot"},
    {"id": 3, "petId": 8, "date": "2013-01-03", "description": "neutered"}
  ]
}
```

### Spring:
```json
{
  "items": [
    {"id": 1, "date": "2013-01-01", "description": "rabies shot", "petId": 7},
    {"id": 4, "date": "2013-01-04", "description": "spayed", "petId": 7},
    {"id": 2, "date": "2013-01-02", "description": "rabies shot", "petId": 8},
    {"id": 3, "date": "2013-01-03", "description": "neutered", "petId": 8}
  ]
}
```

### Verdict: **MINOR DIFFERENCE** -- Same JSON key ordering difference as #7. Functionally equivalent.

---

## 9. GET /owners/6/pets/7/visits (direct per-pet visits)

### Status Code
**[MATCH]** Both return `HTTP 200 OK`

### Content-Type
**[MATCH]** Both return `Content-Type: application/json`

### Response Structure
**[MATCH]** Both return a bare JSON array (no wrapper), consistent with the contrast against the `/pets/visits?petId=` endpoint which uses the `{"items": [...]}` wrapper.

### Visit Data Values
**[MATCH]** Both return the same 2 visits for pet 7.

### Field Ordering Within Visit Object
**[DIFFERENCE]** Same pattern: Python has `petId` second, Spring has `petId` last.

### Python:
```json
[
  {"id": 1, "petId": 7, "date": "2013-01-01", "description": "rabies shot"},
  {"id": 4, "petId": 7, "date": "2013-01-04", "description": "spayed"}
]
```

### Spring:
```json
[
  {"id": 1, "date": "2013-01-01", "description": "rabies shot", "petId": 7},
  {"id": 4, "date": "2013-01-04", "description": "spayed", "petId": 7}
]
```

### Verdict: **MINOR DIFFERENCE** -- Same JSON key ordering difference. Functionally equivalent.

---

## 10. GET /api/gateway/owners/1 (BFF aggregation -- no visits)

### Status Code
**[MATCH]** Both return `HTTP 200 OK`

### Content-Type
**[MATCH]** Both return `Content-Type: application/json`

### Owner Fields
**[MATCH]** `id`, `firstName`, `lastName`, `address`, `city`, `telephone`, `pets` -- all identical values.

### Pet Fields
**[DIFFERENCE]**

| Field | Python | Spring |
|-------|--------|--------|
| `id` | Present | Present |
| `name` | Present | Present |
| `birthDate` | Present | Present |
| `type.name` | Present | Present |
| `type.id` | Present | **MISSING IN SPRING** |
| `visits` | Present (empty array) | Present (empty array) |

### Python:
```json
{
  "id": 1,
  "firstName": "George",
  "lastName": "Franklin",
  "address": "110 W. Liberty St.",
  "city": "Madison",
  "telephone": "6085551023",
  "pets": [
    {
      "id": 1,
      "name": "Leo",
      "birthDate": "2010-09-07",
      "type": {"id": 1, "name": "cat"},
      "visits": []
    }
  ]
}
```

### Spring:
```json
{
  "id": 1,
  "firstName": "George",
  "lastName": "Franklin",
  "address": "110 W. Liberty St.",
  "city": "Madison",
  "telephone": "6085551023",
  "pets": [
    {
      "id": 1,
      "name": "Leo",
      "birthDate": "2010-09-07",
      "type": {"name": "cat"},
      "visits": []
    }
  ]
}
```

### Verdict: **DIFFERENCE** -- In the BFF response, Spring's `type` object contains only `name` (no `id`). Python's BFF includes both `type.id` and `type.name`. This is because the Spring BFF uses a different DTO for the aggregated response that drops `type.id`. The Python version is returning *more* data than Spring, which is generally safe for consumers but is not a faithful reproduction.

---

## 11. GET /api/gateway/owners/6 (BFF aggregation -- with visits)

### Status Code
**[MATCH]** Both return `HTTP 200 OK`

### Content-Type
**[MATCH]** Both return `Content-Type: application/json`

### Owner Fields
**[MATCH]** All owner fields identical.

### Pet Order
**[MATCH]** Both return Max (id=8) before Samantha (id=7), alphabetically by name.

### Visit Data
**[MATCH]** Both correctly merge visits into the corresponding pet's `visits` array:
- Max (pet 8): visit ids 2, 3
- Samantha (pet 7): visit ids 1, 4

### Visit Field Ordering
**[MATCH]** Both use `id`, `petId`, `date`, `description` ordering in BFF visit objects.

### Pet Type in BFF
**[DIFFERENCE]** Same as endpoint #10:

| Field | Python | Spring |
|-------|--------|--------|
| `type.id` | Present | **MISSING IN SPRING** |
| `type.name` | Present | Present |

### Python:
```json
{
  "id": 6,
  "firstName": "Jean",
  "lastName": "Coleman",
  "address": "105 N. Lake St.",
  "city": "Monona",
  "telephone": "6085552654",
  "pets": [
    {
      "id": 8,
      "name": "Max",
      "birthDate": "2012-09-04",
      "type": {"id": 1, "name": "cat"},
      "visits": [
        {"id": 2, "petId": 8, "date": "2013-01-02", "description": "rabies shot"},
        {"id": 3, "petId": 8, "date": "2013-01-03", "description": "neutered"}
      ]
    },
    {
      "id": 7,
      "name": "Samantha",
      "birthDate": "2012-09-04",
      "type": {"id": 1, "name": "cat"},
      "visits": [
        {"id": 1, "petId": 7, "date": "2013-01-01", "description": "rabies shot"},
        {"id": 4, "petId": 7, "date": "2013-01-04", "description": "spayed"}
      ]
    }
  ]
}
```

### Spring:
```json
{
  "id": 6,
  "firstName": "Jean",
  "lastName": "Coleman",
  "address": "105 N. Lake St.",
  "city": "Monona",
  "telephone": "6085552654",
  "pets": [
    {
      "id": 8,
      "name": "Max",
      "birthDate": "2012-09-04",
      "type": {"name": "cat"},
      "visits": [
        {"id": 2, "petId": 8, "date": "2013-01-02", "description": "rabies shot"},
        {"id": 3, "petId": 8, "date": "2013-01-03", "description": "neutered"}
      ]
    },
    {
      "id": 7,
      "name": "Samantha",
      "birthDate": "2012-09-04",
      "type": {"name": "cat"},
      "visits": [
        {"id": 1, "petId": 7, "date": "2013-01-01", "description": "rabies shot"},
        {"id": 4, "petId": 7, "date": "2013-01-04", "description": "spayed"}
      ]
    }
  ]
}
```

### Verdict: **DIFFERENCE** -- Same `type.id` discrepancy as #10. Python includes `type.id` in the BFF pet type; Spring does not. Everything else matches exactly.

---

## 12. GET /actuator/health

### Status Code
**[MATCH]** Both return `HTTP 200 OK` on all services

### Response Body
**[MATCH]** Both return `{"status":"UP"}`

### Content-Type
**[DIFFERENCE]**

| Version | Content-Type |
|---------|-------------|
| Python | `application/json` |
| Spring | `application/vnd.spring-boot.actuator.v3+json` |

### Python (all services):
```
HTTP/1.1 200 OK
Content-Type: application/json
{"status":"UP"}
```

### Spring (example: gateway 8080):
```
HTTP/1.1 200 OK
Content-Type: application/vnd.spring-boot.actuator.v3+json
{"status":"UP"}
```

### Verdict: **DIFFERENCE** -- The response body is identical, but the Content-Type header differs. Spring uses the Spring Boot Actuator vendor media type `application/vnd.spring-boot.actuator.v3+json`. Python uses standard `application/json`. Most clients handle both, but clients that check the Content-Type strictly may behave differently.

---

## 13. GET /actuator/info

### Status Code
**[MATCH]** Both return `HTTP 200 OK`

### Content-Type
**[DIFFERENCE]**

| Version | Content-Type |
|---------|-------------|
| Python | `application/json` |
| Spring | `application/vnd.spring-boot.actuator.v3+json` |

### Response Structure
**[DIFFERENCE]** The structures differ significantly.

### Python (example: api-gateway on 8080):
```json
{
  "build": {
    "artifact": "api-gateway",
    "version": "1.0.0"
  },
  "git": {
    "branch": "main",
    "commit": "unknown"
  }
}
```

### Spring (api-gateway on 8080):
```json
{
  "git": {
    "branch": "main",
    "commit": {
      "id": "b6eaebf",
      "time": "2025-04-27T17:31:36Z"
    }
  },
  "build": {
    "encoding": {
      "reporting": "UTF-8",
      "source": "UTF-8"
    },
    "java": {
      "version": "17"
    },
    "version": "3.4.1",
    "artifact": "spring-petclinic-api-gateway",
    "name": "spring-petclinic-api-gateway",
    "time": "2025-08-31T15:10:17.637Z",
    "group": "org.springframework.samples.petclinic.api"
  }
}
```

### Field-by-Field Comparison

| Field Path | Python | Spring | Status |
|-----------|--------|--------|--------|
| `git.branch` | `"main"` | `"main"` | [MATCH] |
| `git.commit` | `"unknown"` (string) | `{"id": "b6eaebf", "time": "..."}` (object) | [DIFFERENCE] |
| `build.artifact` | `"api-gateway"` | `"spring-petclinic-api-gateway"` | [DIFFERENCE] |
| `build.version` | `"1.0.0"` | `"3.4.1"` | [DIFFERENCE] |
| `build.name` | not present | `"spring-petclinic-api-gateway"` | [MISSING IN PYTHON] |
| `build.time` | not present | `"2025-08-31T15:10:17.637Z"` | [MISSING IN PYTHON] |
| `build.group` | not present | `"org.springframework.samples.petclinic.api"` | [MISSING IN PYTHON] |
| `build.encoding` | not present | `{"reporting":"UTF-8","source":"UTF-8"}` | [MISSING IN PYTHON] |
| `build.java` | not present | `{"version":"17"}` | [MISSING IN PYTHON] |

### Key Structural Differences

1. **`git.commit`**: Python returns a flat string `"unknown"`. Spring returns a nested object with `id` and `time`.
2. **`build.artifact`**: Python uses short service names (e.g., `"api-gateway"`). Spring uses full Maven artifact names (e.g., `"spring-petclinic-api-gateway"`).
3. **`build.version`**: Python hardcodes `"1.0.0"`. Spring reports the actual Maven build version `"3.4.1"`.
4. **Missing fields in Python**: `build.name`, `build.time`, `build.group`, `build.encoding`, `build.java` are all absent.

### Verdict: **SIGNIFICANT DIFFERENCE** -- The info endpoint has a simplified structure in Python compared to Spring's rich build metadata. The `git.commit` type mismatch (string vs object) is the most notable structural incompatibility. However, since actuator/info is typically consumed by monitoring tools rather than application logic, this may be acceptable depending on requirements.

---

## Overall Difference Summary

### Differences Found

| Category | Description | Severity | Endpoints Affected |
|----------|-------------|----------|-------------------|
| **Missing field** | Python `/vets` lacks `nrOfSpecialties` | Medium | #6 |
| **Extra field** | Python BFF includes `type.id` that Spring BFF omits | Low | #10, #11 |
| **JSON key ordering** | Visit objects: Python puts `petId` second, Spring puts it last | Cosmetic | #7, #8, #9 |
| **Content-Type** | Health/info: Python uses `application/json`, Spring uses `application/vnd.spring-boot.actuator.v3+json` | Low | #12, #13 |
| **Structure** | Actuator info: Python uses simplified schema vs Spring's rich build metadata | Medium | #13 |

### What Matches Perfectly

- All owner data (GET /owners, GET /owners/{id})
- Non-existent owner handling (200 + null)
- Pet types list with correct sort order
- Pet detail endpoint with owner as "firstName lastName" string
- Visit wrapper semantics (`{"items":[...]}` vs bare array `[...]`)
- BFF aggregation logic (visit merging into pet objects)
- All data values (names, dates, IDs, descriptions)
- Pet sort ordering within owners (alphabetical by name)

### Recommended Fixes (Priority Order)

1. **Add `nrOfSpecialties` to vets response** -- This is a computed field (`len(specialties)`) that Spring includes via a JPA `@Transient` getter. Adding it to the Python serializer is trivial and restores full compatibility.

2. **Remove `type.id` from BFF pet type** -- The Spring BFF uses a different DTO (`PetDetails`) that intentionally drops the type ID. The Python BFF should strip `type.id` from the aggregated response to match.

3. **Update actuator Content-Type** (optional) -- Return `application/vnd.spring-boot.actuator.v3+json` for actuator endpoints to match Spring Boot's behavior. This matters only if monitoring tools check the media type.

4. **Enrich actuator/info** (optional) -- The simplified info structure is a design choice. If full fidelity is required, restructure `git.commit` as an object and add build metadata fields.
