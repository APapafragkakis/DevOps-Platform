import logging
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)


def setup_tracing(app, db_engine):
    # Exporter reads OTEL_EXPORTER_OTLP_ENDPOINT, e.g. http://jaeger:4318
    if not os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        logger.info("OTEL_EXPORTER_OTLP_ENDPOINT not set, tracing disabled")
        return

    service_name = os.getenv("OTEL_SERVICE_NAME", "devops-platform")
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app, excluded_urls="health,metrics")
    SQLAlchemyInstrumentor().instrument(engine=db_engine)
    logger.info("tracing enabled, exporting to %s", os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))
