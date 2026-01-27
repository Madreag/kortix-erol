"""
Litestar Application Lifespan

Handles startup/shutdown with cache warming.
"""

from contextlib import asynccontextmanager
from litestar import Litestar
from core.utils.logger import logger


async def warm_caches():
    """Warm critical caches on startup."""
    logger.info("[LITESTAR] Starting cache warmup...")
    
    try:
        from core.services import redis as redis_service
        import msgspec
        
        redis = await redis_service.get_client()
        encoder = msgspec.json.Encoder()
        
        # Warm system status cache
        try:
            from core.endpoints.system_status_api import get_system_status_data
            status = await get_system_status_data()
            await redis.set("litestar:system_status", encoder.encode(status), ex=60)
            logger.info("[LITESTAR] Warmed system status cache")
        except Exception as e:
            logger.warning(f"[LITESTAR] Failed to warm system status: {e}")
        
        logger.info("[LITESTAR] Cache warmup complete")
        
    except Exception as e:
        logger.warning(f"[LITESTAR] Cache warmup failed: {e}")


@asynccontextmanager
async def lifespan(app: Litestar):
    """Application lifespan handler."""
    logger.info("[LITESTAR] Starting up v2 API...")
    
    # Warm caches
    await warm_caches()
    
    yield
    
    # Shutdown
    logger.info("[LITESTAR] Shutting down v2 API...")
