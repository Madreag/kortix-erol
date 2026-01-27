"""
Rate Limiting Middleware for Litestar

Token bucket algorithm with separate limits for general and streaming endpoints.
"""

from collections import defaultdict
from time import time
from typing import TYPE_CHECKING

from litestar.middleware import AbstractMiddleware
from litestar.exceptions import TooManyRequestsException
from litestar.types import ASGIApp, Receive, Scope, Send

if TYPE_CHECKING:
    pass


class RateLimitMiddleware(AbstractMiddleware):
    """
    Token bucket rate limiter for /v2 endpoints.
    
    Limits:
    - 100 requests per minute per IP (general)
    - 20 requests per minute per IP for /stream (expensive)
    """
    
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.buckets: dict[str, dict] = defaultdict(lambda: {"tokens": 100, "last": time()})
        self.stream_buckets: dict[str, dict] = defaultdict(lambda: {"tokens": 20, "last": time()})
        
        # Configuration
        self.general_rate = 100  # requests per minute
        self.stream_rate = 20   # requests per minute for streaming
        self.window = 60.0      # seconds
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Extract client IP
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"
        
        # Get path
        path = scope.get("path", "")
        
        # Choose bucket based on path
        is_stream = "/stream" in path
        buckets = self.stream_buckets if is_stream else self.buckets
        rate = self.stream_rate if is_stream else self.general_rate
        
        # Token bucket algorithm
        bucket = buckets[client_ip]
        now = time()
        elapsed = now - bucket["last"]
        
        # Refill tokens
        bucket["tokens"] = min(rate, bucket["tokens"] + (elapsed * rate / self.window))
        bucket["last"] = now
        
        # Check if request allowed
        if bucket["tokens"] < 1:
            retry_after = int(self.window - elapsed)
            raise TooManyRequestsException(
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            )
        
        # Consume token
        bucket["tokens"] -= 1
        
        await self.app(scope, receive, send)
