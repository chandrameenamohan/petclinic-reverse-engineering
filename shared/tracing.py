"""Shared OpenTelemetry tracing setup for all petclinic services.

Provides ``setup_tracing(app, service_name)`` which configures:
- B3 propagation (Spring Cloud Sleuth compatible)
- Zipkin JSON exporter
- 100% sampling (TraceIdRatioBased 1.0)
- Auto-instrumentation: FastAPI, httpx, SQLAlchemy (if engine provided)
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.zipkin.json import ZipkinExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
from sqlalchemy.ext.asyncio import AsyncEngine


def setup_tracing(
    app: FastAPI,
    service_name: str,
    *,
    engine: AsyncEngine | None = None,
    zipkin_endpoint: str | None = None,
) -> None:
    """Configure OpenTelemetry tracing with Zipkin export and B3 propagation.

    Args:
        app: FastAPI application to instrument.
        service_name: Logical service name (appears in Zipkin UI).
        engine: Async SQLAlchemy engine to instrument (DB-backed services only).
        zipkin_endpoint: Zipkin collector URL. Falls back to ``ZIPKIN_ENDPOINT``
            env var, then ``http://localhost:9411/api/v2/spans``.
    """
    endpoint = zipkin_endpoint or os.getenv(
        "ZIPKIN_ENDPOINT",
        "http://localhost:9411/api/v2/spans",
    )

    # B3 multi-header propagation (X-B3-TraceId, X-B3-SpanId, X-B3-Sampled)
    set_global_textmap(B3MultiFormat())

    # Resource identifying this service in Zipkin
    resource = Resource.create({"service.name": service_name})

    # 100% sampling — capture every request
    sampler = TraceIdRatioBased(1.0)

    # Tracer provider with Zipkin export
    provider = TracerProvider(resource=resource, sampler=sampler)
    exporter = ZipkinExporter(endpoint=endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # Auto-instrument FastAPI (inbound HTTP)
    FastAPIInstrumentor.instrument_app(app)

    # Auto-instrument httpx (outbound HTTP — B3 headers propagated automatically)
    HTTPXClientInstrumentor().instrument()

    # Auto-instrument SQLAlchemy (DB queries) if engine provided
    if engine is not None:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
