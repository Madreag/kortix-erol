import os
import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI
    from litestar import Litestar
    from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


def setup_telemetry(
    app: "FastAPI",
    engine: Optional["AsyncEngine"] = None
) -> Optional[object]:
    """
    Configure OpenTelemetry for distributed tracing.
    
    Args:
        app: FastAPI application instance
        engine: SQLAlchemy async engine (optional)
        
    Returns:
        Tracer instance if telemetry is enabled, None otherwise
    """
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not otlp_endpoint:
        logger.info("OpenTelemetry disabled (OTEL_EXPORTER_OTLP_ENDPOINT not set)")
        return None
    
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    except ImportError as e:
        logger.warning(f"OpenTelemetry packages not installed: {e}")
        return None
    
    resource = Resource.create({
        SERVICE_NAME: os.environ.get("OTEL_SERVICE_NAME", "kortix-backend"),
    })
    
    provider = TracerProvider(resource=resource)
    
    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    
    trace.set_tracer_provider(provider)
    
    FastAPIInstrumentor.instrument_app(app)
    
    if engine:
        try:
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
            SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
        except Exception as e:
            logger.warning(f"Failed to instrument SQLAlchemy: {e}")
    
    RedisInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
    
    logger.info(f"OpenTelemetry configured with endpoint: {otlp_endpoint}")
    
    return trace.get_tracer(__name__)


def get_tracer(name: str = __name__) -> object:
    """Get a tracer for manual instrumentation."""
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except ImportError:
        return None


def setup_litestar_telemetry(litestar_app: "Litestar") -> None:
    """
    Configure OpenTelemetry for Litestar /v2 routes.
    
    Args:
        litestar_app: Litestar application instance
    """
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not otlp_endpoint:
        logger.info("OpenTelemetry disabled for Litestar (OTEL_EXPORTER_OTLP_ENDPOINT not set)")
        return
    
    try:
        from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
        litestar_app.asgi_handler = OpenTelemetryMiddleware(litestar_app.asgi_handler)
        logger.info("OpenTelemetry configured for Litestar /v2 routes")
    except ImportError as e:
        logger.warning(f"OpenTelemetry ASGI middleware not installed: {e}")
    except Exception as e:
        logger.error(f"Failed to setup Litestar telemetry: {e}")
