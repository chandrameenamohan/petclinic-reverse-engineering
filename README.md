# Spring Petclinic Microservices -> Python/FastAPI

Complete rewrite of the [Spring Petclinic Microservices](https://github.com/spring-petclinic/spring-petclinic-microservices) reference application from Java/Spring Boot to Python/FastAPI, preserving API compatibility, architecture patterns, and operational behavior.

## Architecture

```
                        ┌──────────────────┐
                        │   API Gateway    │
                        │   (port 8080)    │
                        │   HTMX + Jinja2  │
                        └───────┬──────────┘
                                │
               ┌────────────────┼────────────────┐
               │                │                │
     ┌─────────▼──────┐ ┌──────▼─────────┐ ┌────▼───────────┐
     │   Customers    │ │     Visits     │ │      Vets      │
     │   Service      │ │    Service     │ │    Service     │
     │  (port 8081)   │ │  (port 8082)   │ │  (port 8083)   │
     └────────────────┘ └────────────────┘ └────────────────┘
               │                │                │
               └────────────────┼────────────────┘
                                │
     ┌──────────────────────────┼──────────────────────────┐
     │                          │                          │
┌────▼───────────┐  ┌──────────▼────────┐  ┌──────────────▼──┐
│  Config Server │  │ Discovery Server  │  │  GenAI Service  │
│  (port 8888)   │  │   (port 8761)     │  │  (port 8084)    │
└────────────────┘  └───────────────────┘  └─────────────────┘
                                │
                    ┌───────────▼──────────┐
                    │   Admin Server      │
                    │   (port 9090)       │
                    └─────────────────────┘

Observability: Prometheus (9091) | Grafana (3000) | Zipkin (9411)
```

## Tech Stack

| Layer          | Technology                                 |
|----------------|--------------------------------------------|
| Web framework  | FastAPI + Uvicorn                          |
| ORM            | SQLAlchemy 2.0 (async)                     |
| Validation     | Pydantic v2                                |
| Frontend       | HTMX + Jinja2 templates                   |
| GenAI          | OpenAI API + ChromaDB (RAG)               |
| Observability  | Prometheus, Grafana, Zipkin (OpenTelemetry)|
| Containers     | Docker Compose                             |
| Language       | Python 3.11+                               |

## Services

| Service           | Port | Description                                  |
|-------------------|------|----------------------------------------------|
| API Gateway       | 8080 | Frontend UI, reverse proxy to backend APIs   |
| Customers Service | 8081 | Owners and pets CRUD                         |
| Visits Service    | 8082 | Visit scheduling and history                 |
| Vets Service      | 8083 | Veterinarians and specialties                |
| GenAI Service     | 8084 | AI-powered chat with RAG over vet data       |
| Config Server     | 8888 | Centralized YAML configuration               |
| Discovery Server  | 8761 | Service registry and health dashboard        |
| Admin Server      | 9090 | Aggregated health monitoring dashboard       |

## Quick Start

### Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/)
- Docker and Docker Compose (for full stack)

### Local Development

```bash
# Install dependencies
poetry install

# Copy environment config
cp .env.example .env

# Run a single service (e.g., customers)
poetry run uvicorn customers_service.main:app --port 8081 --reload
```

### Docker Compose (Full Stack)

```bash
docker compose up --build
```

This starts all 8 microservices plus Zipkin, Prometheus, and Grafana. The UI is available at [http://localhost:8080](http://localhost:8080).

## Observability

- **Zipkin** tracing UI: [http://localhost:19411](http://localhost:19411)
- **Prometheus** metrics: [http://localhost:19091](http://localhost:19091)
- **Grafana** dashboards: [http://localhost:13030](http://localhost:13030)

All services export OpenTelemetry traces (B3 propagation) and Prometheus metrics out of the box.

## Documentation

Detailed design specs are in the [`docs/`](docs/) folder:

- [00 - Overview](docs/00-overview.md)
- [01 - Architecture](docs/01-architecture.md)
- [02 - Data Models](docs/02-data-models.md)
- [03 - API Specification](docs/03-api-spec.md)
- [04 - Infrastructure](docs/04-infrastructure.md)
- [05 - Inter-Service Communication](docs/05-inter-service-communication.md)
- [06 - GenAI Service](docs/06-genai-service.md)
- [07 - Frontend](docs/07-frontend.md)
- [08 - Testing](docs/08-testing.md)

## Reference

This project is a Python/FastAPI port of the [Spring Petclinic Microservices](https://github.com/spring-petclinic/spring-petclinic-microservices) reference application by the Spring community.
