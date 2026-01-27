"""
Metrics Route for Litestar V2

Exposes performance metrics for monitoring and verification.
"""

from litestar import Controller, get

from litestar_app.metrics import metrics
from core.config.feature_flags import FeatureFlags


class MetricsController(Controller):
    """Controller for performance metrics endpoints."""
    
    path = "/metrics"
    tags = ["Metrics"]
    
    @get("/")
    async def get_metrics(self) -> dict:
        """
        Get current performance metrics.
        
        Returns latency percentiles, cache stats, error rates, and pass/fail status.
        """
        data = metrics.get_metrics()
        data["feature_flags"] = FeatureFlags.get_status()
        return data
    
    @get("/summary")
    async def get_metrics_summary(self) -> dict:
        """
        Get condensed metrics summary for quick health checks.
        """
        data = metrics.get_metrics()
        return {
            "status": "healthy" if data["status"]["all_ok"] else "degraded",
            "p50_ms": data["latency"]["global"]["p50_ms"],
            "cache_hit_rate": data["cache"]["hit_rate_percent"],
            "error_rate_5xx": data["errors"]["error_rate_5xx_percent"],
            "circuit_breaker_open": data["circuit_breaker"]["open"],
            "uptime_seconds": data["uptime_seconds"],
            "checks": data["status"],
        }
    
    @get("/reset", include_in_schema=False)
    async def reset_metrics(self) -> dict:
        """
        Reset metrics (for testing only).
        """
        global metrics
        from litestar_app.metrics import MetricsCollector
        MetricsCollector._instance = None
        metrics = MetricsCollector()
        return {"status": "reset"}
