# 04 - Infrastructure Specification

> Monitoring, tracing, deployment, and observability configuration for the Spring Petclinic Microservices system.
> Source: docker-compose.yml, docker/, pom.xml, and application configuration files.

---

## Table of Contents

1. [Docker Build Pipeline](#1-docker-build-pipeline)
2. [Docker Compose Deployment](#2-docker-compose-deployment)
3. [Prometheus Metrics](#3-prometheus-metrics)
4. [Grafana Dashboards](#4-grafana-dashboards)
5. [Distributed Tracing (Zipkin)](#5-distributed-tracing-zipkin)
6. [Spring Boot Admin](#6-spring-boot-admin)
7. [Health Checks](#7-health-checks)
8. [Centralized Configuration](#8-centralized-configuration)
9. [Service Discovery (Eureka)](#9-service-discovery-eureka)
10. [Python Equivalents](#10-python-equivalents)

---

## 1. Docker Build Pipeline

### 1.1 Multi-Stage Dockerfile

Source: `docker/Dockerfile`

The project uses a shared multi-stage Dockerfile for all Spring Boot services:

```dockerfile
FROM eclipse-temurin:17 AS builder
WORKDIR application
ARG ARTIFACT_NAME
COPY ${ARTIFACT_NAME}.jar application.jar
RUN java -Djarmode=layertools -jar application.jar extract

FROM eclipse-temurin:17
WORKDIR application
ARG EXPOSED_PORT
EXPOSE ${EXPOSED_PORT}
ENV SPRING_PROFILES_ACTIVE=docker
COPY --from=builder application/dependencies/ ./
RUN true
COPY --from=builder application/spring-boot-loader/ ./
RUN true
COPY --from=builder application/snapshot-dependencies/ ./
RUN true
COPY --from=builder application/application/ ./
ENTRYPOINT ["java", "org.springframework.boot.loader.launch.JarLauncher"]
```

**Key aspects:**
- **Base image:** Eclipse Temurin JDK 17 (both build and runtime stages)
- **Layer extraction:** Uses Spring Boot's `jarmode=layertools` to split the fat JAR into layers for optimal Docker caching:
  - `dependencies/` - third-party libraries (rarely changes)
  - `spring-boot-loader/` - Spring Boot launcher
  - `snapshot-dependencies/` - snapshot dependencies
  - `application/` - the actual application code (changes most often)
- **Profile activation:** Sets `SPRING_PROFILES_ACTIVE=docker` as environment variable
- **`RUN true` workaround:** Required for btrfs filesystem compatibility (Docker layer creation bug)

### 1.2 Maven Build Integration

Source: parent `pom.xml`, `buildDocker` profile

The Docker build is integrated into Maven via `exec-maven-plugin`:

```xml
<profile>
    <id>buildDocker</id>
    <!-- Uses exec-maven-plugin to invoke docker/podman build -->
</profile>
```

**Build command:**
```bash
./mvnw clean install -PbuildDocker
# Or with Podman:
./mvnw clean install -PbuildDocker -Dcontainer.executable=podman
```

**Configuration properties:**
| Property | Default | Description |
|----------|---------|-------------|
| `docker.image.prefix` | `springcommunity` | Image name prefix |
| `container.executable` | `docker` | Container runtime (`docker` or `podman`) |
| `container.platform` | `linux/amd64` | Target platform (use `linux/arm64` for Apple Silicon) |
| `container.build.extraarg` | `--load` | Extra build argument |

**Per-service port configuration:**
| Service | Exposed Port | Property in pom.xml |
|---------|-------------|---------------------|
| config-server | 8888 | `docker.image.exposed.port` |
| discovery-server | 8761 | `docker.image.exposed.port` |
| customers-service | 8081 | `docker.image.exposed.port` |
| visits-service | 8082 | `docker.image.exposed.port` |
| vets-service | 8083 | `docker.image.exposed.port` |
| genai-service | 8084 | `docker.image.exposed.port` |
| api-gateway | 8080 | `docker.image.exposed.port` |
| admin-server | 9090 | `docker.image.exposed.port` |

**Resulting image names:** `springcommunity/spring-petclinic-{module-name}`

---

## 2. Docker Compose Deployment

Source: `docker-compose.yml`

### 2.1 Service Definitions

```
docker-compose.yml
  +-- config-server        (port 8888, 512M)
  +-- discovery-server     (port 8761, 512M, depends: config-server)
  +-- customers-service    (port 8081, 512M, depends: config-server, discovery-server)
  +-- visits-service       (port 8082, 512M, depends: config-server, discovery-server)
  +-- vets-service         (port 8083, 512M, depends: config-server, discovery-server)
  +-- genai-service        (port 8084, 512M, depends: config-server, discovery-server)
  +-- api-gateway          (port 8080, 512M, depends: config-server, discovery-server)
  +-- admin-server         (port 9090, 512M, depends: config-server, discovery-server)
  +-- tracing-server       (port 9411, 512M, Zipkin)
  +-- grafana-server       (port 3030->3000, 256M, custom build)
  +-- prometheus-server    (port 9091->9090, 256M, custom build)
```

### 2.2 Startup Order and Dependencies

The system has a strict startup dependency chain:

```
config-server (must be healthy first)
    |
    +-- discovery-server (must be healthy)
            |
            +-- customers-service
            +-- visits-service
            +-- vets-service
            +-- genai-service
            +-- api-gateway
            +-- admin-server

tracing-server (independent, no dependencies)
grafana-server (independent, no dependencies)
prometheus-server (independent, no dependencies)
```

**Health check configuration for startup ordering:**

**config-server:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-I", "http://config-server:8888"]
  interval: 5s
  timeout: 5s
  retries: 10
```

**discovery-server:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://discovery-server:8761"]
  interval: 5s
  timeout: 3s
  retries: 10
```

All business services use `condition: service_healthy` to wait for both config-server and discovery-server.

### 2.3 Memory Limits

| Service Category | Memory Limit |
|-----------------|-------------|
| Application services | 512M each |
| Infrastructure (Grafana, Prometheus) | 256M each |
| Tracing server (Zipkin) | 512M |

**Total memory:** ~5.5 GB for the full stack.

### 2.4 Port Mappings

| Service | Host Port | Container Port |
|---------|-----------|---------------|
| config-server | 8888 | 8888 |
| discovery-server | 8761 | 8761 |
| customers-service | 8081 | 8081 |
| visits-service | 8082 | 8082 |
| vets-service | 8083 | 8083 |
| genai-service | 8084 | 8084 |
| api-gateway | 8080 | 8080 |
| admin-server | 9090 | 9090 |
| tracing-server (Zipkin) | 9411 | 9411 |
| grafana-server | 3030 | 3000 |
| prometheus-server | 9091 | 9090 |

### 2.5 Environment Variables

The genai-service requires API keys injected via environment variables:

```yaml
genai-service:
  environment:
    - OPENAI_API_KEY=${OPENAI_API_KEY}
    - AZURE_OPENAI_KEY=${AZURE_OPENAI_KEY}
    - AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
```

---

## 3. Prometheus Metrics

### 3.1 Prometheus Configuration

Source: `docker/prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: ['localhost:9090']

  - job_name: api-gateway
    metrics_path: /actuator/prometheus
    static_configs:
      - targets: ['api-gateway:8080']

  - job_name: customers-service
    metrics_path: /actuator/prometheus
    static_configs:
      - targets: ['customers-service:8081']

  - job_name: visits-service
    metrics_path: /actuator/prometheus
    static_configs:
      - targets: ['visits-service:8082']

  - job_name: vets-service
    metrics_path: /actuator/prometheus
    static_configs:
      - targets: ['vets-service:8083']
```

**Key details:**
- Scrape interval: 15 seconds
- Metrics path: `/actuator/prometheus` (Spring Boot Actuator endpoint)
- Services scraped: api-gateway, customers, visits, vets (NOT genai-service or admin-server)
- Prometheus image: `prom/prometheus:v2.4.2`

### 3.2 Spring Boot Actuator Metrics Dependencies

Each business service includes these dependencies for metrics:

```xml
<!-- Prometheus metrics registry -->
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-registry-prometheus</artifactId>
</dependency>

<!-- Micrometer observation API -->
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-observation</artifactId>
</dependency>

<!-- DataSource metrics -->
<dependency>
    <groupId>net.ttddyy.observation</groupId>
    <artifactId>datasource-micrometer-spring-boot</artifactId>
</dependency>
```

### 3.3 Custom Metrics via @Timed Annotations

The controllers use Micrometer `@Timed` annotations to produce custom metrics:

| Annotation | Controller | Metrics Produced |
|-----------|-----------|-----------------|
| `@Timed("petclinic.owner")` | `OwnerResource` | `petclinic_owner_seconds_count`, `petclinic_owner_seconds_sum`, `petclinic_owner_seconds_max` |
| `@Timed("petclinic.pet")` | `PetResource` | `petclinic_pet_seconds_count`, `petclinic_pet_seconds_sum`, `petclinic_pet_seconds_max` |
| `@Timed("petclinic.visit")` | `VisitResource` | `petclinic_visit_seconds_count`, `petclinic_visit_seconds_sum`, `petclinic_visit_seconds_max` |

These metrics include labels: `method` (Java method name), `exception`, `status`, etc.

### 3.4 Standard Spring Boot Actuator Metrics

Additionally, Spring Boot Actuator automatically provides:

- `http_server_requests_seconds_*` - HTTP request latency and count
- `jvm_memory_*` - JVM memory usage
- `jvm_gc_*` - Garbage collection metrics
- `system_cpu_*` - CPU usage
- `process_uptime_seconds` - Process uptime
- `hikaricp_*` - Connection pool metrics (for JPA services)
- `spring_data_repository_invocations_*` - Repository call metrics

---

## 4. Grafana Dashboards

### 4.1 Grafana Configuration

Source: `docker/grafana/`

- **Image:** `grafana/grafana:5.2.4`
- **Host port:** 3030 (mapped to container port 3000)
- **Authentication:** Anonymous access enabled with Admin role (development mode)
- **Datasource:** Prometheus at `http://prometheus-server:9090` (auto-provisioned)

**grafana.ini key settings:**
```ini
app_mode = development
[server]
enable_gzip = true
[auth.anonymous]
enabled = true
org_role = Admin
```

### 4.2 Pre-configured Dashboard

Source: `docker/grafana/dashboards/grafana-petclinic-dashboard.json`

The dashboard is auto-provisioned on startup and includes these panels:

| Panel | Type | PromQL Query |
|-------|------|-------------|
| **HTTP Request Latency** | Graph | `sum(rate(http_server_requests_seconds_sum{status!~"5.."}[1m]))/sum(rate(http_server_requests_seconds_count{status!~"5.."}[1m]))` (avg) and `max(http_server_requests_seconds_max{status!~"5.."})` (max) |
| **HTTP Request Activity** | Graph | `sum(rate(http_server_requests_seconds_count[1m]))` (total) and `sum(rate(http_server_requests_seconds_count{status=~"5.."}[1m]))` (5xx errors) |
| **Owners Updated** | Singlestat | `sum(petclinic_owner_seconds_count{method="updateOwner", exception="none"})` |
| **Owners Created** | Singlestat | `sum(petclinic_owner_seconds_count{method="createOwner", exception="none"})` |
| **Pets Created** | Singlestat | `sum(petclinic_pet_seconds_count{method="processCreationForm", exception="none"})` |
| **Visits Created** | Singlestat | `sum(petclinic_visit_seconds_count{method="read", exception="none"})` |
| **SPC Business Histogram** | Graph | Combines owner create/update, pet create, and visit create metrics over time |

### 4.3 Dashboard Provisioning

Source: `docker/grafana/provisioning/`

**Datasources** (`provisioning/datasources/all.yml`):
```yaml
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus-server:9090
    is_default: true
```

**Dashboards** (`provisioning/dashboards/all.yml`):
```yaml
providers:
  - name: 'default'
    type: file
    updateIntervalSeconds: 10
    options:
      path: /var/lib/grafana/dashboards
```

---

## 5. Distributed Tracing (Zipkin)

### 5.1 Zipkin Server

- **Image:** `openzipkin/zipkin`
- **Port:** 9411
- **No dependencies** - runs independently

### 5.2 Tracing Dependencies (per service)

Each business service includes these tracing dependencies:

```xml
<!-- Micrometer tracing bridge for Brave -->
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-tracing-bridge-brave</artifactId>
</dependency>

<!-- Zipkin reporter for Brave -->
<dependency>
    <groupId>io.zipkin.reporter2</groupId>
    <artifactId>zipkin-reporter-brave</artifactId>
</dependency>

<!-- OpenTelemetry Zipkin exporter -->
<dependency>
    <groupId>io.opentelemetry</groupId>
    <artifactId>opentelemetry-exporter-zipkin</artifactId>
</dependency>
```

### 5.3 Tracing Architecture

```
[api-gateway] --trace--> [Zipkin :9411]
     |
     +--[customers-service] --trace--> [Zipkin :9411]
     +--[visits-service] --trace--> [Zipkin :9411]
     +--[vets-service] --trace--> [Zipkin :9411]
     +--[genai-service] --trace--> [Zipkin :9411]
```

**Trace propagation:**
- Uses Micrometer Tracing with Brave as the tracer
- Trace context is propagated via HTTP headers (B3 propagation format)
- Each service reports spans to Zipkin at `http://tracing-server:9411`
- Traces span across services (e.g., a gateway request to customers-service and visits-service shows as a single distributed trace)

### 5.4 Configuration

Tracing is configured via Spring Cloud Config. The typical configuration (from the external config repo) includes:
```yaml
management:
  tracing:
    sampling:
      probability: 1.0  # Sample 100% of requests
  zipkin:
    tracing:
      endpoint: http://tracing-server:9411/api/v2/spans
```

---

## 6. Spring Boot Admin

### 6.1 Admin Server

- **Port:** 9090
- **Image:** `springcommunity/spring-petclinic-admin-server`
- **Dependencies:** config-server, discovery-server

Spring Boot Admin provides a web UI for monitoring and managing Spring Boot applications. It discovers services via Eureka and provides:

- Application health status overview
- Environment properties viewer
- Log level management at runtime
- JVM metrics (memory, threads, GC)
- HTTP request metrics
- Spring beans listing
- Scheduled tasks overview

### 6.2 Build Info

All services include `spring-boot-maven-plugin` with `build-info` goal and `git-commit-id-maven-plugin`, which generates:
- `META-INF/build-info.properties` - build timestamp, version, etc.
- `git.properties` - git commit hash, branch, etc.

These are exposed via Spring Boot Actuator's `/actuator/info` endpoint and displayed in Admin Server.

---

## 7. Health Checks

### 7.1 Actuator Health Endpoints

All services include `spring-boot-starter-actuator` which provides:

| Endpoint | Description |
|----------|-------------|
| `/actuator/health` | Service health status |
| `/actuator/info` | Build and git info |
| `/actuator/prometheus` | Prometheus metrics |
| `/actuator/env` | Environment properties |
| `/actuator/beans` | Spring beans |
| `/actuator/loggers` | Log level management |

### 7.2 Docker Health Checks

Only infrastructure services have Docker-level health checks:

| Service | Health Check | Interval | Timeout | Retries |
|---------|-------------|----------|---------|---------|
| config-server | `curl -I http://config-server:8888` | 5s | 5s | 10 |
| discovery-server | `curl -f http://discovery-server:8761` | 5s | 3s | 10 |

Business services do NOT have Docker health checks -- they rely on Eureka registration for service availability detection.

---

## 8. Centralized Configuration

### 8.1 Config Server

Source: `spring-petclinic-config-server/src/main/resources/application.yml`

- **Port:** 8888
- **Backend:** Git repository at `https://github.com/spring-petclinic/spring-petclinic-microservices-config`
- **Branch:** `main`
- **Alternative:** Native filesystem backend via `GIT_REPO` env var and `native` profile

### 8.2 Client Configuration Pattern

Each service includes this in its `application.yml`:

```yaml
spring:
  config:
    import: optional:configserver:${CONFIG_SERVER_URL:http://localhost:8888/}

---
spring:
  config:
    activate:
      on-profile: docker
    import: configserver:http://config-server:8888
```

**Key points:**
- In local development: config-server at `http://localhost:8888` (optional -- services start even if config-server is down)
- In Docker: config-server at `http://config-server:8888` (required via the `docker` profile)
- The `docker` profile is activated automatically by the Dockerfile's `ENV SPRING_PROFILES_ACTIVE=docker`

### 8.3 Externalized Configuration

The external git config repository (`spring-petclinic-microservices-config`) stores per-service YAML files:
- `application.yml` - shared configuration
- `customers-service.yml` - service-specific config
- `visits-service.yml`
- `vets-service.yml`
- `api-gateway.yml`
- etc.

Typical externalized settings include: server ports, Eureka URLs, Zipkin endpoint, management endpoints exposure, database connection strings.

---

## 9. Service Discovery (Eureka)

### 9.1 Discovery Server

- **Port:** 8761
- **Image:** `springcommunity/spring-petclinic-discovery-server`
- **Web UI:** `http://localhost:8761`

### 9.2 Client Registration

All business services include:
```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-netflix-eureka-client</artifactId>
</dependency>
```

Services register with Eureka at startup using their `spring.application.name` as the service ID.

### 9.3 Service Resolution

The API Gateway and genai-service use Eureka-resolved service names in their HTTP calls:
- `http://customers-service/owners` - resolved via Eureka to actual host:port
- `http://visits-service/pets/visits` - resolved via Eureka
- `http://vets-service/vets` - resolved via Eureka
- Gateway routes use `lb://service-name` prefix for load-balanced routing

---

## 10. Python Equivalents

### 10.1 Docker Build (Python)

Replace the multi-stage Spring Boot Dockerfile with a Python equivalent:

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
EXPOSE ${EXPOSED_PORT:-8000}
ENV ENVIRONMENT=docker
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${EXPOSED_PORT:-8000}"]
```

### 10.2 Docker Compose (Python)

```yaml
services:
  customers-service:
    build:
      context: ./customers-service
      args:
        EXPOSED_PORT: 8081
    container_name: customers-service
    deploy:
      resources:
        limits:
          memory: 256M  # Python services need less memory than JVM
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/customers
      - SERVICE_REGISTRY_URL=http://consul:8500
      - ZIPKIN_ENDPOINT=http://tracing-server:9411/api/v2/spans
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
      interval: 5s
      timeout: 3s
      retries: 10
    ports:
      - "8081:8081"
    depends_on:
      postgres:
        condition: service_healthy
      consul:
        condition: service_healthy
```

### 10.3 Prometheus Metrics (Python)

Use `prometheus_client` or `prometheus-fastapi-instrumentator`:

```python
# requirements.txt
prometheus-fastapi-instrumentator==7.0.0
prometheus_client==0.21.0

# main.py
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram

app = FastAPI()
Instrumentator().instrument(app).expose(app, endpoint="/actuator/prometheus")

# Custom metrics equivalent to @Timed annotations
OWNER_REQUESTS = Histogram(
    "petclinic_owner_seconds",
    "Owner endpoint request duration",
    ["method", "exception"],
)
PET_REQUESTS = Histogram(
    "petclinic_pet_seconds",
    "Pet endpoint request duration",
    ["method", "exception"],
)
VISIT_REQUESTS = Histogram(
    "petclinic_visit_seconds",
    "Visit endpoint request duration",
    ["method", "exception"],
)


# Usage in endpoints:
@router.post("/owners", status_code=201)
async def create_owner(request: OwnerRequest, db: AsyncSession = Depends(get_db)):
    with OWNER_REQUESTS.labels(method="createOwner", exception="none").time():
        owner = Owner(**request.model_dump())
        db.add(owner)
        await db.commit()
        return owner
```

**Prometheus config stays the same** -- just update the `metrics_path` if needed:
```yaml
scrape_configs:
  - job_name: customers-service
    metrics_path: /actuator/prometheus  # Or /metrics if using default
    static_configs:
      - targets: ['customers-service:8081']
```

### 10.4 Distributed Tracing (Python)

Replace Micrometer/Brave/Zipkin with OpenTelemetry:

```python
# requirements.txt
opentelemetry-api==1.27.0
opentelemetry-sdk==1.27.0
opentelemetry-exporter-zipkin==1.27.0
opentelemetry-instrumentation-fastapi==0.48b0
opentelemetry-instrumentation-httpx==0.48b0
opentelemetry-instrumentation-sqlalchemy==0.48b0

# tracing.py
from opentelemetry import trace
from opentelemetry.exporter.zipkin.json import ZipkinExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor


def setup_tracing(app: FastAPI, service_name: str):
    provider = TracerProvider(
        resource=Resource.create({"service.name": service_name})
    )
    zipkin_exporter = ZipkinExporter(
        endpoint=os.getenv("ZIPKIN_ENDPOINT", "http://tracing-server:9411/api/v2/spans")
    )
    provider.add_span_processor(BatchSpanProcessor(zipkin_exporter))
    trace.set_tracer_provider(provider)

    # Auto-instrument FastAPI, httpx, and SQLAlchemy
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument(engine=engine)
```

### 10.5 Health Checks (Python)

```python
from fastapi import APIRouter

actuator_router = APIRouter(prefix="/actuator", tags=["actuator"])


@actuator_router.get("/health")
async def health():
    return {
        "status": "UP",
        "components": {
            "db": {"status": "UP"},
            "diskSpace": {"status": "UP"},
        },
    }


@actuator_router.get("/info")
async def info():
    return {
        "build": {
            "artifact": "customers-service",
            "version": "1.0.0",
        },
        "git": {
            "branch": os.getenv("GIT_BRANCH", "main"),
            "commit": os.getenv("GIT_COMMIT", "unknown"),
        },
    }
```

### 10.6 Centralized Configuration (Python)

Replace Spring Cloud Config Server with one of:

**Option A: Consul KV (recommended -- also serves as service registry)**
```python
import consul

c = consul.Consul(host="consul", port=8500)
_, data = c.kv.get("config/customers-service/database_url")
DATABASE_URL = data["Value"].decode()
```

**Option B: Environment variables with .env files (simplest)**
```python
# .env.docker
DATABASE_URL=postgresql://user:pass@postgres:5432/customers
EUREKA_URL=http://consul:8500
ZIPKIN_ENDPOINT=http://tracing-server:9411/api/v2/spans

# Python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite:///./local.db"
    service_registry_url: str = "http://localhost:8500"
    zipkin_endpoint: str = "http://localhost:9411/api/v2/spans"

    class Config:
        env_file = ".env"
```

### 10.7 Service Discovery (Python)

Replace Eureka with Consul:

```python
# requirements.txt
python-consul2==0.2.0

# discovery.py
import consul
import socket


class ServiceRegistry:
    def __init__(self, consul_host: str = "consul", consul_port: int = 8500):
        self.client = consul.Consul(host=consul_host, port=consul_port)

    def register(self, service_name: str, port: int):
        self.client.agent.service.register(
            name=service_name,
            service_id=f"{service_name}-{socket.gethostname()}",
            address=socket.gethostname(),
            port=port,
            check=consul.Check.http(
                f"http://{socket.gethostname()}:{port}/actuator/health",
                interval="10s",
            ),
        )

    def discover(self, service_name: str) -> str:
        _, services = self.client.health.service(service_name, passing=True)
        if not services:
            raise Exception(f"No healthy instances of {service_name}")
        instance = services[0]
        address = instance["Service"]["Address"]
        port = instance["Service"]["Port"]
        return f"http://{address}:{port}"
```

### 10.8 Spring Boot Admin Equivalent (Python)

For the Python rewrite, consider:

- **Flower** (if using Celery for background tasks)
- **Custom FastAPI admin dashboard** using `sqladmin` for data management
- **Grafana** for operational monitoring (already in the stack)
- **Portainer** for container management

A simple health dashboard can aggregate `/actuator/health` from all services:

```python
# admin-service/main.py
import httpx
from fastapi import FastAPI

app = FastAPI(title="Admin Dashboard")

SERVICES = {
    "customers-service": "http://customers-service:8081",
    "visits-service": "http://visits-service:8082",
    "vets-service": "http://vets-service:8083",
    "genai-service": "http://genai-service:8084",
    "api-gateway": "http://api-gateway:8080",
}


@app.get("/dashboard")
async def dashboard():
    results = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in SERVICES.items():
            try:
                resp = await client.get(f"{url}/actuator/health")
                results[name] = resp.json()
            except Exception:
                results[name] = {"status": "DOWN"}
    return results
```

### 10.9 Chaos Monkey Equivalent (Python)

The Java project includes `chaos-monkey-spring-boot` for resilience testing. Python equivalent:

```python
# chaos.py
import random
import asyncio
from fastapi import Request


async def chaos_middleware(request: Request, call_next):
    if os.getenv("CHAOS_ENABLED") == "true":
        # Random latency injection
        if random.random() < 0.1:  # 10% chance
            await asyncio.sleep(random.uniform(1.0, 5.0))
        # Random failure injection
        if random.random() < 0.05:  # 5% chance
            raise HTTPException(status_code=503, detail="Chaos Monkey!")
    return await call_next(request)
```

---

## Appendix: Complete Infrastructure Stack Summary

| Component | Java Stack | Python Equivalent |
|-----------|-----------|------------------|
| Web Framework | Spring Boot 4 (WebMVC / WebFlux) | FastAPI + Uvicorn |
| API Gateway | Spring Cloud Gateway (WebFlux) | FastAPI reverse proxy or Traefik/Kong |
| Service Discovery | Netflix Eureka | Consul / etcd |
| Config Server | Spring Cloud Config (Git backend) | Consul KV / Environment variables |
| Circuit Breaker | Resilience4J | `pybreaker` / `tenacity` |
| Metrics | Micrometer + Prometheus Registry | `prometheus_client` / `prometheus-fastapi-instrumentator` |
| Tracing | Micrometer Tracing + Brave + Zipkin | OpenTelemetry + Zipkin exporter |
| Admin UI | Spring Boot Admin | Custom dashboard / Grafana |
| Chaos Testing | Chaos Monkey for Spring Boot | Custom middleware / `chaos-toolkit` |
| Container Runtime | Docker / Podman | Docker / Podman (same) |
| Orchestration | Docker Compose | Docker Compose (same) |
| Build Tool | Maven | pip + setuptools / Poetry |
| Logging | SLF4J + Logback | Python `logging` / `structlog` |
