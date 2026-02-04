"""
JWT Authentication Middleware for Litestar

Uses existing Kortix JWT verification.
"""

from litestar.middleware import AbstractAuthenticationMiddleware, AuthenticationResult
from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException
from core.utils.logger import logger


class JWTAuthMiddleware(AbstractAuthenticationMiddleware):
    """JWT Authentication middleware for Litestar /v2 routes."""
    
    # Paths that don't require authentication
    EXCLUDE_PATHS = frozenset({
        "/health",
        "/health/detailed",
        "/metrics",
        "/metrics/summary",
        "/metrics/reset",
        "/docs",
        "/schema",
        "/openapi.json",
    })
    
    async def authenticate_request(self, connection: ASGIConnection) -> AuthenticationResult:
        """Authenticate the request and return user info."""
        
        path = connection.scope.get("path", "")
        
        # Skip auth for excluded paths
        if path in self.EXCLUDE_PATHS or path.startswith("/docs") or path.startswith("/schema"):
            return AuthenticationResult(user=None, auth=None)
        
        auth_header = connection.headers.get("Authorization", "")
        
        if not auth_header.startswith("Bearer "):
            raise NotAuthorizedException("Missing or invalid authorization header")
        
        token = auth_header[7:]
        
        try:
            # Use existing Kortix JWT verification (sync version for HS256)
            from core.utils.auth_utils import _decode_jwt_with_verification
            payload = _decode_jwt_with_verification(token)
            
            # Validate required claims
            sub = payload.get("sub")
            if not sub:
                logger.warning("[LITESTAR] Token missing required 'sub' claim")
                raise NotAuthorizedException("Invalid token: missing required claims")
            
            user = {
                "user_id": sub,
                "account_id": payload.get("account_id") or sub,
                "email": payload.get("email"),
            }
            
            return AuthenticationResult(user=user, auth=payload)
            
        except Exception as e:
            logger.warning(f"[LITESTAR] Token validation failed: {e}")
            raise NotAuthorizedException("Invalid or expired token")
