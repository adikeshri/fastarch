"""OpenTelemetry setup: tracer/meter providers + auto-instrumentation hooks (PRD §38).

Exporters are OTLP-over-HTTP and only configured when
``ObservabilitySettings.otlp_endpoint`` is set — in local dev without a
collector running, spans/metrics are created (so code paths are exercised)
but simply not exported anywhere.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.infrastructure.configuration.settings import ObservabilitySettings

if TYPE_CHECKING:
    from fastapi import FastAPI
    from sqlalchemy.ext.asyncio import AsyncEngine


def configure_observability(settings: ObservabilitySettings) -> None:
    resource = Resource.create({SERVICE_NAME: settings.service_name})

    if settings.traces_enabled:
        tracer_provider = TracerProvider(resource=resource)
        if settings.otlp_endpoint:
            tracer_provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{settings.otlp_endpoint}/v1/traces"))
            )
        trace.set_tracer_provider(tracer_provider)

    if settings.metrics_enabled:
        readers = []
        if settings.otlp_endpoint:
            readers.append(
                PeriodicExportingMetricReader(
                    OTLPMetricExporter(endpoint=f"{settings.otlp_endpoint}/v1/metrics")
                )
            )
        metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=readers))


def instrument_fastapi(app: FastAPI) -> None:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app)


def instrument_sqlalchemy(engine: AsyncEngine) -> None:
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
