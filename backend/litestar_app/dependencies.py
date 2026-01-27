"""
Litestar Dependency Injection

Shares existing Kortix infrastructure:
- SQLAlchemy engine (connection pooling, read replicas)
- Redis client (StreamHub, caching)
- JWT authentication
"""

from typing import AsyncIterator, Optional
from litestar import Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.services.db import get_session, QueryType
from core.services import redis as redis_service
from core.utils.logger import logger


async def provide_db_session() -> AsyncIterator[AsyncSession]:
    """
    Provide SQLAlchemy async session using existing Kortix engine.
    
    Uses get_session() which provides:
    - Connection pooling (3 + 7 overflow per worker)
    - Supavisor auto-detection for NullPool
    - Transient error retry logic
    - Read replica routing (via QueryType.READ)
    """
    async with get_session(QueryType.READ) as session:
        yield session


async def provide_redis():
    """
    Provide Redis client using existing Kortix connection pool.
    
    Reuses existing client - don't create new connections.
    """
    return await redis_service.get_client()


async def provide_current_user(request: Request) -> Optional[dict]:
    """
    Extract and validate current user from JWT token.
    
    Returns None for unauthenticated requests (handled by middleware).
    """
    auth_header = request.headers.get("Authorization", "")
    
    if not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header[7:]
    
    try:
        # Use existing Kortix JWT verification (sync version for HS256)
        from core.utils.auth_utils import _decode_jwt_with_verification
        payload = _decode_jwt_with_verification(token)
        
        return {
            "user_id": payload.get("sub"),
            "account_id": payload.get("account_id") or payload.get("sub"),
            "email": payload.get("email"),
        }
    except Exception as e:
        logger.debug(f"JWT verification failed: {e}")
        return None
