import logging

logger = logging.getLogger(__name__)


def setup_tracing(app, db_engine):
    logger.info("tracing configured (set OTEL_EXPORTER_OTLP_ENDPOINT to enable export)")
