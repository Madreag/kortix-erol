"""
Metrics Collection Middleware for Litestar V2

Automatically collects latency, cache, and error metrics for all requests.
"""

import time

from litestar.types import ASGIApp, Receive, Scope, Send


def create_metrics_middleware(app: ASGIApp) -> ASGIApp:
    """Factory function to create metrics middleware."""
    
    async def metrics_middleware(scope: Scope, receive: Receive, send: Send) -> None:
        """Collect performance metrics for V2 API requests."""
        # Only process HTTP requests
        if scope["type"] != "http":
            await app(scope, receive, send)
            return
        
        # Skip metrics/health endpoints to avoid noise
        path = scope.get("path", "")
        if path.startswith("/metrics") or path.startswith("/health"):
            await app(scope, receive, send)
            return
        
        from litestar_app.metrics import metrics
        
        start_time = time.perf_counter()
        status_code = 200
        cache_hit = None
        
        async def send_wrapper(message: dict) -> None:
            nonlocal status_code, cache_hit
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
                # Check for cache hit header
                headers = message.get("headers", [])
                for name, value in headers:
                    if name == b"x-cache":
                        cache_hit = value == b"HIT"
                        break
            await send(message)
        
        try:
            await app(scope, receive, send_wrapper)
        finally:
            # Calculate latency and record synchronously (non-blocking)
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            # Record metrics (fire-and-forget, non-blocking)
            try:
                # Use synchronous recording to avoid coroutine issues
                metrics.record_request_sync(
                    endpoint=path,
                    latency_ms=latency_ms,
                    status_code=status_code,
                    cache_hit=cache_hit,
                )
            except Exception:
                pass  # Don't let metrics collection break requests
    
    return metrics_middleware


# Wrapper class for Litestar middleware compatibility
class MetricsMiddleware:
    """Metrics middleware wrapper for Litestar."""
    
    def __init__(self, app: ASGIApp) -> None:
        self.app = create_metrics_middleware(app)
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.app(scope, receive, send)
