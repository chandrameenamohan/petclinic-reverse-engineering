# Shared multi-stage Dockerfile for all petclinic-python services.
# Build context must be the project root (petclinic-python/).
#
# Usage:
#   docker build -f docker/Dockerfile \
#     --build-arg SERVICE_NAME=customers_service \
#     --build-arg EXPOSED_PORT=8081 \
#     -t petclinic/customers-service .

# ---------- Stage 1: builder ----------
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build tooling
RUN pip install --no-cache-dir poetry==2.1.1 poetry-plugin-export

# Copy dependency files first for layer caching
COPY pyproject.toml poetry.lock ./

# Export production deps to requirements.txt and install with pip
RUN poetry export -f requirements.txt --without dev -o requirements.txt && \
    pip install --no-cache-dir --prefix=/install --ignore-installed -r requirements.txt

# ---------- Stage 2: runtime ----------
FROM python:3.12-slim

# Install curl for Docker health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ARG SERVICE_NAME
ARG EXPOSED_PORT=8000

# Persist ARGs as ENV so CMD can reference them at runtime
ENV SERVICE_NAME=${SERVICE_NAME} \
    EXPOSED_PORT=${EXPOSED_PORT} \
    ENVIRONMENT=docker \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy shared library (used by all services)
COPY shared/ ./shared/

# Copy per-service YAML configs (may be empty during early development)
COPY config/ ./config/

# Copy the target service module
COPY ${SERVICE_NAME}/ ./${SERVICE_NAME}/

EXPOSE ${EXPOSED_PORT}

# Shell form required for variable expansion
CMD uvicorn ${SERVICE_NAME}.main:app --host 0.0.0.0 --port ${EXPOSED_PORT}
