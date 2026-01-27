"""
Health Check Routes for Litestar /v2 API

Provides basic and detailed health checks.
"""

from datetime import datetime, timezone
from typing import Any
from litestar import Controller, get
from litestar.status_codes import HTTP_200_OK
from core.services.db import get_db_stats
from core.utils.instance import INSTANCE_ID
import os


class HealthController(Controller):
    """Health check endpoints for /v2 API."""
    
    path = "/health"
    tags = ["system"]
    
    @get("/", status_code=HTTP_200_OK, exclude_from_auth=True)
    async def health_check(self) -> dict[str, Any]:
        """Basic health check."""
        return {
            "status": "healthy",
            "engine": "litestar",
            "version": "2.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "instance_id": INSTANCE_ID,
        }
    
    @get("/detailed", status_code=HTTP_200_OK, exclude_from_auth=True)
    async def detailed_health(self, redis: Any) -> dict[str, Any]:
        """Detailed health check with component status."""
        
        # Check Redis
        redis_status = "healthy"
        redis_latency_ms = None
        try:
            import time
            start = time.perf_counter()
            await redis.ping()
            redis_latency_ms = (time.perf_counter() - start) * 1000
        except Exception as e:
            redis_status = f"unhealthy: {str(e)}"
        
        # Get DB stats
        db_stats = get_db_stats()
        
        return {
            "status": "healthy" if redis_status == "healthy" else "degraded",
            "components": {
                "redis": {
                    "status": redis_status,
                    "latency_ms": round(redis_latency_ms, 2) if redis_latency_ms else None,
                },
                "database": {
                    "replica_reads": db_stats.get("replica_reads", 0),
                    "primary_reads": db_stats.get("primary_reads", 0),
                    "replica_fallbacks": db_stats.get("replica_fallbacks", 0),
                },
            },
            "engine": "litestar",
            "version": os.environ.get("APP_VERSION", "2.0"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "instance_id": INSTANCE_ID,
        }
