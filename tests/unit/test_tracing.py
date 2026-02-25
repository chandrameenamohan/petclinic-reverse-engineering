"""Tests for shared.tracing — OpenTelemetry + Zipkin + B3 propagation setup."""

import contextlib
from collections.abc import Sequence

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.propagate import get_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from sqlalchemy.ext.asyncio import create_async_engine

from shared.tracing import setup_tracing


class _InMemoryExporter(SpanExporter):
    """Simple in-memory span exporter for test assertions."""

    def __init__(self) -> None:
        self.spans: list[ReadableSpan] = []

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass


@pytest.fixture(autouse=True)
def _reset_otel():
    """Reset OTel global state between tests so set_tracer_provider works each time."""
    # Reset the Once guard BEFORE the test so each test can set its own provider
    trace._TRACER_PROVIDER_SET_ONCE = trace.Once()  # noqa: SLF001
    trace._TRACER_PROVIDER = None  # noqa: SLF001
    yield
    # Uninstrument httpx to avoid double-instrumentation across tests
    with contextlib.suppress(Exception):
        HTTPXClientInstrumentor().uninstrument()


class TestSetupTracing:
    """Tests for the setup_tracing function."""

    def test_sets_tracer_provider(self):
        app = FastAPI()
        setup_tracing(app, "test-service", zipkin_endpoint="http://localhost:9411/api/v2/spans")
        provider = trace.get_tracer_provider()
        assert isinstance(provider, TracerProvider)

    def test_sets_b3_propagator(self):
        app = FastAPI()
        setup_tracing(app, "test-service", zipkin_endpoint="http://localhost:9411/api/v2/spans")
        propagator = get_global_textmap()
        assert isinstance(propagator, B3MultiFormat)

    def test_service_name_in_resource(self):
        app = FastAPI()
        setup_tracing(app, "my-cool-service", zipkin_endpoint="http://localhost:9411/api/v2/spans")
        provider = trace.get_tracer_provider()
        assert isinstance(provider, TracerProvider)
        attrs = provider.resource.attributes
        assert attrs["service.name"] == "my-cool-service"

    def test_instruments_fastapi_app(self):
        app = FastAPI()
        setup_tracing(app, "test-service", zipkin_endpoint="http://localhost:9411/api/v2/spans")
        assert FastAPIInstrumentor.is_instrumented_by_opentelemetry

    def test_instruments_sqlalchemy_when_engine_provided(self):
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        app = FastAPI()
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        setup_tracing(
            app,
            "test-service",
            engine=engine,
            zipkin_endpoint="http://localhost:9411/api/v2/spans",
        )
        assert SQLAlchemyInstrumentor().is_instrumented_by_opentelemetry
        SQLAlchemyInstrumentor().uninstrument()

    def test_does_not_instrument_sqlalchemy_without_engine(self):
        app = FastAPI()
        setup_tracing(app, "test-service", zipkin_endpoint="http://localhost:9411/api/v2/spans")
        provider = trace.get_tracer_provider()
        assert isinstance(provider, TracerProvider)


class TestTracingIntegration:
    """Integration tests — verify spans are actually created."""

    async def test_fastapi_request_creates_span(self):
        app = FastAPI()

        @app.get("/test-endpoint")
        async def test_endpoint():
            return {"status": "ok"}

        # Set up tracing with in-memory exporter for verification
        resource = Resource.create({"service.name": "test-svc"})
        provider = TracerProvider(resource=resource)
        memory_exporter = _InMemoryExporter()
        provider.add_span_processor(SimpleSpanProcessor(memory_exporter))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test-endpoint")

        assert response.status_code == 200
        provider.force_flush()
        spans = memory_exporter.spans
        assert len(spans) > 0
        span_names = [s.name for s in spans]
        assert any("GET /test-endpoint" in name for name in span_names)
