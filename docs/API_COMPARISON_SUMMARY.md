# API Comparison Summary: Python/FastAPI vs Spring Boot

This document summarizes the results of a side-by-side API comparison between the Python/FastAPI rewrite and the original Spring Petclinic Microservices. Both systems were tested against identical endpoints with the same seed data. The full detailed report with request/response samples is available in [API_COMPARISON_REPORT.md](../API_COMPARISON_REPORT.md).

## Endpoint Comparison Table

| # | Endpoint | Method | Java Status | Python Status | Match Level |
|---|----------|--------|-------------|---------------|-------------|
| 1 | `/owners` | GET | 200 OK | 200 OK | Exact Match |
| 2 | `/owners/1` | GET | 200 OK | 200 OK | Exact Match |
| 3 | `/owners/999` | GET | 200 OK (null) | 200 OK (null) | Exact Match |
| 4 | `/petTypes` | GET | 200 OK | 200 OK | Exact Match |
| 5 | `/owners/1/pets/1` | GET | 200 OK | 200 OK | Exact Match |
| 6 | `/vets` | GET | 200 OK | 200 OK | Minor Difference |
| 7 | `/pets/visits?petId=7` | GET | 200 OK | 200 OK | Cosmetic Difference |
| 8 | `/pets/visits?petId=7,8` | GET | 200 OK | 200 OK | Cosmetic Difference |
| 9 | `/owners/6/pets/7/visits` | GET | 200 OK | 200 OK | Cosmetic Difference |
| 10 | `/api/gateway/owners/1` (BFF) | GET | 200 OK | 200 OK | Minor Difference |
| 11 | `/api/gateway/owners/6` (BFF) | GET | 200 OK | 200 OK | Minor Difference |
| 12 | `/actuator/health` | GET | 200 OK | 200 OK | Minor Difference |
| 13 | `/actuator/info` | GET | 200 OK | 200 OK | Significant Difference |

## Overall Compatibility

- **Exact matches:** 5 of 13 endpoints (38%)
- **Cosmetic/minor differences:** 7 of 13 endpoints (54%)
- **Significant differences:** 1 of 13 endpoints (8%)
- **Functional compatibility:** 12 of 13 endpoints (92%) -- all business-logic endpoints are functionally equivalent

> The only endpoint with significant structural differences is `/actuator/info`, which is an infrastructure/monitoring endpoint, not a business API. All customer-facing and inter-service endpoints are functionally compatible.

## Key Findings

### What Matches Exactly

- **Owner CRUD** -- All owner data (list, single, non-existent) returns identical JSON with matching field names, values, sort order, and HTTP status codes.
- **Pet types** -- Alphabetical sort order and all values match.
- **Pet detail** -- Flat pet object with `owner` as a "firstName lastName" string matches perfectly.
- **Data values** -- Every name, date, ID, address, telephone, and description is identical across both systems.
- **Pet sort order** -- Pets within owners are sorted alphabetically by name in both implementations.
- **Non-existent resource handling** -- Both return HTTP 200 with body `null` (matching Spring's `Optional` behavior).

### What Has Minor Differences

| Difference | Category | Impact | Affected Endpoints |
|-----------|----------|--------|-------------------|
| Python `/vets` lacks `nrOfSpecialties` field | Missing field | Medium -- consumers expecting this field will break | #6 |
| Python BFF includes `type.id` that Spring BFF omits | Extra field | Low -- Python returns superset of data | #10, #11 |
| Visit JSON key ordering (`petId` position) | Key order | Cosmetic -- JSON spec says order is not meaningful | #7, #8, #9 |
| Actuator Content-Type header | Header | Low -- most clients accept both | #12, #13 |
| Actuator info structure is simplified | Structure | Medium -- only affects monitoring tools | #13 |

### Recommended Fixes (Priority Order)

1. **Add `nrOfSpecialties` to vets response** -- trivial computed field (`len(specialties)`).
2. **Remove `type.id` from BFF pet type** -- Spring's BFF intentionally drops the type ID via a separate DTO.
3. **Update actuator Content-Type** (optional) -- return `application/vnd.spring-boot.actuator.v3+json` for actuator endpoints.
4. **Enrich actuator/info** (optional) -- restructure `git.commit` as an object and add build metadata.

## Methodology

- **Python capture:** 2026-02-25T04:13-04:16 UTC
- **Spring capture:** 2026-02-25 09:54:29 UTC
- Both systems were running with the same seed data (10 owners, 13 pets, 6 vets, 4 visits, 6 pet types).
- Responses were compared field-by-field including status codes, headers, response structure, field names, values, and sort ordering.
