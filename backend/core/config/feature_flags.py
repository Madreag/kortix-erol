"""
Feature Flags for Litestar /v2 API Rollout

Provides gradual traffic shifting and automatic rollback capabilities.
"""

import os


class FeatureFlags:
    """Feature flags for gradual rollout of Litestar backend."""
    
    # Master switch for Litestar /v2 endpoints
    ENABLE_LITESTAR_V2: bool = os.environ.get("ENABLE_LITESTAR_V2", "true").lower() == "true"
    
    # Traffic percentage to route to Litestar (0-100)
    # Used by frontend circuit breaker for V2 preference
    LITESTAR_TRAFFIC_PERCENT: int = int(os.environ.get("LITESTAR_TRAFFIC_PERCENT", "100"))
    
    # Automatic rollback threshold (5xx error rate %)
    ROLLBACK_ERROR_THRESHOLD: float = float(os.environ.get("ROLLBACK_ERROR_THRESHOLD", "1.0"))
    
    @classmethod
    def should_use_litestar(cls, request_id: str = "") -> bool:
        """Determine if request should use Litestar based on traffic split."""
        if not cls.ENABLE_LITESTAR_V2:
            return False
        if cls.LITESTAR_TRAFFIC_PERCENT >= 100:
            return True
        if cls.LITESTAR_TRAFFIC_PERCENT <= 0:
            return False
        # Consistent hashing for same requests
        return hash(request_id) % 100 < cls.LITESTAR_TRAFFIC_PERCENT
    
    @classmethod
    def get_status(cls) -> dict:
        """Get current feature flag status."""
        return {
            "litestar_v2_enabled": cls.ENABLE_LITESTAR_V2,
            "traffic_percent": cls.LITESTAR_TRAFFIC_PERCENT,
            "rollback_threshold": cls.ROLLBACK_ERROR_THRESHOLD,
        }
