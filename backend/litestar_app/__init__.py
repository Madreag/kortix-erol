"""
Litestar v2 Application for Kortix /v2 API

High-performance backend using:
- Litestar framework (40-60% faster than FastAPI)
- msgspec for serialization (~65% faster than Pydantic)
- uvloop for async event loop (Linux/macOS only)
- Redis response caching

Mounted alongside FastAPI at /v2 for gradual rollout.
"""

from litestar import Litestar
from litestar.config.cors import CORSConfig
from litestar.config.compression import CompressionConfig
from litestar.logging import LoggingConfig
from litestar.openapi import OpenAPIConfig
from litestar.di import Provide

from .routes import health, threads, projects, agents, metrics
from .dependencies import provide_db_session, provide_redis, provide_current_user
from .middleware import JWTAuthMiddleware, MetricsMiddleware, RateLimitMiddleware
from .exception_handlers import exception_handlers
from .lifespan import lifespan
from core.utils.config import config, EnvMode


def create_litestar_app() -> Litestar:
    """Create and configure Litestar application for /v2 API."""
    
    # CORS configuration (matches FastAPI config)
    allowed_origins = [
        "https://www.kortix.com",
        "https://kortix.com",
        "https://dev.kortix.com",
        "https://staging.kortix.com",
    ]
    
    if config.ENV_MODE == EnvMode.LOCAL:
        allowed_origins.extend(["http://localhost:3000", "http://127.0.0.1:3000"])
    
    cors_config = CORSConfig(
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Project-Id", "X-API-Key"],
    )
    
    compression_config = CompressionConfig(
        backend="gzip",
        minimum_size=500,
    )
    
    logging_config = LoggingConfig(
        log_exceptions="always",
        traceback_line_limit=20,
    )
    
    openapi_config = OpenAPIConfig(
        title="Kortix API v2",
        version="2.0.0",
        description="High-performance API (Litestar + msgspec)",
        path="/docs",
    )
    
    app = Litestar(
        route_handlers=[
            health.HealthController,
            threads.ThreadsController,
            projects.ProjectsController,
            agents.AgentsController,
            metrics.MetricsController,
        ],
        cors_config=cors_config,
        compression_config=compression_config,
        logging_config=logging_config,
        openapi_config=openapi_config,
        exception_handlers=exception_handlers,
        dependencies={
            "db_session": Provide(provide_db_session),
            "redis": Provide(provide_redis),
            "current_user": Provide(provide_current_user),
        },
        middleware=[RateLimitMiddleware, MetricsMiddleware, JWTAuthMiddleware],
        lifespan=[lifespan],
        debug=config.ENV_MODE == EnvMode.LOCAL,
    )
    
    return app


# Create app instance for mounting
litestar_app = create_litestar_app()
