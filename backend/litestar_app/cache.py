"""
Response Cache Decorator for Litestar

High-performance Redis caching with msgspec serialization.
"""

from functools import wraps
from typing import Optional, Callable, Any, List
import msgspec
from core.services import redis as redis_service
from core.utils.logger import logger

# Use msgspec for maximum serialization performance
encoder = msgspec.json.Encoder()
decoder = msgspec.json.Decoder()


def _json_dumps(obj: Any) -> bytes:
    """Fast JSON serialization with msgspec."""
    return encoder.encode(obj)


def _json_loads(data: bytes) -> Any:
    """Fast JSON deserialization with msgspec."""
    return decoder.decode(data)


def cached_response(
    ttl: int = 60,
    key_prefix: str = "v2:response",
    vary_on: Optional[List[str]] = None,
    vary_on_user: bool = True,
):
    """
    Cache API response in Redis with msgspec serialization.
    
    Args:
        ttl: Cache TTL in seconds
        key_prefix: Redis key prefix
        vary_on: List of parameter names to include in cache key
        vary_on_user: Whether to include user/account in cache key
    
    Usage:
        @get("/threads")
        @cached_response(ttl=30, vary_on=["page", "limit"])
        async def get_threads(page: int = 1, limit: int = 20, current_user: dict) -> ThreadListDTO:
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            key_parts = [key_prefix, func.__name__]
            
            # Add user/account to key if needed
            if vary_on_user:
                user = kwargs.get('current_user') or {}
                account_id = user.get('account_id') if isinstance(user, dict) else None
                if account_id:
                    key_parts.append(f"user:{account_id}")
            
            # Add varied parameters to key
            if vary_on:
                for param in vary_on:
                    if param in kwargs:
                        key_parts.append(f"{param}:{kwargs[param]}")
            
            cache_key = ":".join(key_parts)
            
            # Try to get from cache
            try:
                redis = await redis_service.get_client()
                cached = await redis.get(cache_key)
                if cached:
                    logger.debug(f"[CACHE] HIT: {cache_key}")
                    return _json_loads(cached)
            except Exception as e:
                logger.warning(f"[CACHE] Read error: {e}")
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result (serialize msgspec structs)
            try:
                if hasattr(result, '__class__') and hasattr(result.__class__, '__mro__'):
                    # Check if it's a msgspec Struct
                    if msgspec.Struct in result.__class__.__mro__:
                        data = encoder.encode(result)
                    else:
                        data = _json_dumps(result)
                else:
                    data = _json_dumps(result)
                await redis.set(cache_key, data, ex=ttl)
                logger.debug(f"[CACHE] SET: {cache_key} (TTL: {ttl}s)")
            except Exception as e:
                logger.warning(f"[CACHE] Write error: {e}")
            
            return result
        return wrapper
    return decorator


async def invalidate_cache(patterns: List[str]):
    """
    Invalidate cache entries matching patterns.
    
    Usage:
        await invalidate_cache(["v2:response:get_threads:user:123:*"])
    """
    try:
        redis = await redis_service.get_client()
        for pattern in patterns:
            keys = await redis.keys(pattern)
            if keys:
                await redis.delete(*keys)
                logger.debug(f"[CACHE] Invalidated {len(keys)} keys matching {pattern}")
    except Exception as e:
        logger.warning(f"[CACHE] Invalidation error: {e}")


async def invalidate_user_cache(account_id: str, resources: Optional[List[str]] = None):
    """
    Helper to invalidate all caches for a user's resources.
    
    Usage:
        await invalidate_user_cache("user123", ["threads", "projects"])
    """
    patterns = [f"v2:response:*:user:{account_id}:*"]
    return await invalidate_cache(patterns)
