"""
OpenTelemetry Configuration for Distributed Tracing

Configures OpenTelemetry instrumentation for:
- FastAPI automatic instrumentation
- Database query tracing (SQLAlchemy, MongoDB, Redis)
- HTTP client tracing
- Custom span creation
- Trace export to Jaeger/OTLP
"""

import os
import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor

logger = logging.getLogger(__name__)


def configure_opentelemetry(
    service_name: str = "amharic-doc-backend",
    service_version: str = "1.0.0",
    otlp_endpoint: Optional[str] = None,
    enable_console_export: bool = False,
) -> TracerProvider:
    """
    Configure OpenTelemetry tracing.

    Args:
        service_name: Service identifier for traces
        service_version: Service version
        otlp_endpoint: OTLP collector endpoint (e.g., "http://jaeger:4317")
        enable_console_export: Enable console span export for debugging

    Returns:
        Configured TracerProvider
    """
    # Create resource with service information
    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
            "environment": os.getenv("ENVIRONMENT", "development"),
            "deployment.type": "docker",
        }
    )

    # Create tracer provider
    tracer_provider = TracerProvider(resource=resource)

    # Configure OTLP exporter if endpoint provided
    if otlp_endpoint:
        try:
            otlp_exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                insecure=True,  # Use TLS in production
            )
            tracer_provider.add_span_processor(
                BatchSpanProcessor(otlp_exporter)
            )
            logger.info(f"OpenTelemetry: OTLP exporter configured for {otlp_endpoint}")
        except Exception as e:
            logger.error(f"Failed to configure OTLP exporter: {e}")

    # Add console exporter for debugging
    if enable_console_export:
        console_exporter = ConsoleSpanExporter()
        tracer_provider.add_span_processor(
            BatchSpanProcessor(console_exporter)
        )
        logger.info("OpenTelemetry: Console exporter enabled")

    # Set global tracer provider
    trace.set_tracer_provider(tracer_provider)

    logger.info(f"OpenTelemetry: Tracer provider initialized for {service_name}")

    return tracer_provider


def instrument_fastapi(app):
    """
    Instrument FastAPI application for automatic tracing.

    Args:
        app: FastAPI application instance
    """
    try:
        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls="/health,/metrics",  # Exclude health/metrics endpoints
            tracer_provider=trace.get_tracer_provider(),
        )
        logger.info("OpenTelemetry: FastAPI instrumentation enabled")
    except Exception as e:
        logger.error(f"Failed to instrument FastAPI: {e}")


def instrument_database_clients(
    sqlalchemy_engine=None,
    redis_client=None,
    mongodb_client=None,
):
    """
    Instrument database clients for query tracing.

    Args:
        sqlalchemy_engine: SQLAlchemy engine instance
        redis_client: Redis client instance
        mongodb_client: PyMongo client instance
    """
    # Instrument SQLAlchemy
    if sqlalchemy_engine:
        try:
            SQLAlchemyInstrumentor().instrument(
                engine=sqlalchemy_engine,
                tracer_provider=trace.get_tracer_provider(),
            )
            logger.info("OpenTelemetry: SQLAlchemy instrumentation enabled")
        except Exception as e:
            logger.error(f"Failed to instrument SQLAlchemy: {e}")

    # Instrument Redis
    if redis_client:
        try:
            RedisInstrumentor().instrument(
                tracer_provider=trace.get_tracer_provider(),
            )
            logger.info("OpenTelemetry: Redis instrumentation enabled")
        except Exception as e:
            logger.error(f"Failed to instrument Redis: {e}")

    # Instrument MongoDB
    if mongodb_client:
        try:
            PymongoInstrumentor().instrument(
                tracer_provider=trace.get_tracer_provider(),
            )
            logger.info("OpenTelemetry: PyMongo instrumentation enabled")
        except Exception as e:
            logger.error(f"Failed to instrument PyMongo: {e}")


def instrument_http_clients():
    """
    Instrument HTTP clients for outbound request tracing.
    """
    try:
        RequestsInstrumentor().instrument(
            tracer_provider=trace.get_tracer_provider(),
        )
        logger.info("OpenTelemetry: HTTP client instrumentation enabled")
    except Exception as e:
        logger.error(f"Failed to instrument HTTP clients: {e}")


def get_tracer(name: str = __name__):
    """
    Get a tracer for creating custom spans.

    Args:
        name: Tracer name (typically __name__)

    Returns:
        Tracer instance

    Example:
        tracer = get_tracer(__name__)

        with tracer.start_as_current_span("document_processing") as span:
            span.set_attribute("document.id", doc_id)
            span.set_attribute("document.format", format)
            # ... processing logic ...
            span.add_event("OCR completed", {"confidence": 0.95})
    """
    return trace.get_tracer(name)


def create_span(
    tracer,
    name: str,
    attributes: Optional[dict] = None,
):
    """
    Context manager for creating custom spans.

    Args:
        tracer: Tracer instance
        name: Span name
        attributes: Optional span attributes

    Example:
        tracer = get_tracer(__name__)

        with create_span(tracer, "extract_text", {"format": "pdf"}):
            # ... extraction logic ...
    """
    span = tracer.start_as_current_span(name)
    if attributes:
        for key, value in attributes.items():
            span.set_attribute(key, value)
    return span


# Predefined span attribute keys for consistency
class SpanAttributes:
    """Standard span attribute keys for the application"""

    # Document attributes
    DOCUMENT_ID = "document.id"
    DOCUMENT_FORMAT = "document.format"
    DOCUMENT_SIZE = "document.size_bytes"
    DOCUMENT_PAGES = "document.pages"

    # Processing attributes
    JOB_ID = "job.id"
    JOB_PRIORITY = "job.priority"
    TASK_ID = "task.id"
    TASK_TYPE = "task.type"
    AGENT_NAME = "agent.name"

    # OCR attributes
    OCR_ENGINE = "ocr.engine"
    OCR_LANGUAGE = "ocr.language"
    OCR_CONFIDENCE = "ocr.confidence"

    # Search attributes
    SEARCH_QUERY = "search.query"
    SEARCH_RESULTS_COUNT = "search.results.count"
    SEARCH_DURATION_MS = "search.duration_ms"

    # Export attributes
    EXPORT_FORMAT = "export.format"
    EXPORT_SIZE = "export.size_bytes"

    # Error attributes
    ERROR_TYPE = "error.type"
    ERROR_MESSAGE = "error.message"
    ERROR_STACKTRACE = "error.stacktrace"


# Example usage in application code:
"""
from src.config.opentelemetry import get_tracer, SpanAttributes

tracer = get_tracer(__name__)

async def process_document(document_id: str):
    with tracer.start_as_current_span("process_document") as span:
        span.set_attribute(SpanAttributes.DOCUMENT_ID, document_id)

        try:
            # Extract text
            with tracer.start_as_current_span("extract_text") as extract_span:
                text = await extract_text(document_id)
                extract_span.set_attribute("text.length", len(text))

            # OCR processing
            with tracer.start_as_current_span("ocr") as ocr_span:
                result = await perform_ocr(text)
                ocr_span.set_attribute(SpanAttributes.OCR_CONFIDENCE, result.confidence)
                ocr_span.add_event("OCR completed", {
                    "confidence": result.confidence,
                    "language": "amh"
                })

            span.set_attribute("status", "completed")
            return result

        except Exception as e:
            span.record_exception(e)
            span.set_attribute(SpanAttributes.ERROR_TYPE, type(e).__name__)
            span.set_attribute(SpanAttributes.ERROR_MESSAGE, str(e))
            raise
"""