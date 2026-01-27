import os
import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check():
    """Basic health check."""
    return {"status": "healthy"}


@router.get("/detailed")
async def detailed_health():
    """Detailed health check with component status."""
    from core.services import redis as redis_service
    
    redis_status = "healthy"
    redis_stats = {}
    try:
        redis = await redis_service.get_client()
        await redis.ping()
        if hasattr(redis_service, 'hub'):
            redis_stats = redis_service.hub.get_stats()
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"
        logger.warning(f"Redis health check failed: {e}")
    
    db_status = "healthy"
    db_stats = {}
    try:
        from core.services.db import check_connection, get_stats
        await check_connection()
        db_stats = get_stats()
    except ImportError:
        db_status = "unknown"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        logger.warning(f"Database health check failed: {e}")
    
    overall_status = "healthy"
    if "unhealthy" in redis_status or "unhealthy" in db_status:
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "components": {
            "redis": {
                "status": redis_status,
                "stats": redis_stats,
            },
            "database": {
                "status": db_status,
                "stats": db_stats,
            },
        },
        "version": os.environ.get("APP_VERSION", "unknown"),
    }
