"""
Performance Metrics Collector for Litestar V2

Collects and exposes:
- Request latency percentiles (P50, P95, P99)
- Cache hit/miss rates
- Error counts by status code
- Circuit breaker status
"""

import time
import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Optional
import statistics


@dataclass
class LatencyStats:
    """Latency statistics for a time window."""
    samples: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def record(self, latency_ms: float) -> None:
        """Record a latency sample."""
        self.samples.append(latency_ms)
    
    def percentile(self, p: int) -> Optional[float]:
        """Calculate percentile (0-100)."""
        if not self.samples:
            return None
        sorted_samples = sorted(self.samples)
        idx = int(len(sorted_samples) * p / 100)
        return sorted_samples[min(idx, len(sorted_samples) - 1)]
    
    def mean(self) -> Optional[float]:
        """Calculate mean latency."""
        if not self.samples:
            return None
        return statistics.mean(self.samples)


@dataclass  
class CacheStats:
    """Cache hit/miss statistics."""
    hits: int = 0
    misses: int = 0
    
    def record_hit(self) -> None:
        self.hits += 1
    
    def record_miss(self) -> None:
        self.misses += 1
    
    @property
    def total(self) -> int:
        return self.hits + self.misses
    
    @property
    def hit_rate(self) -> float:
        """Hit rate as percentage (0-100)."""
        if self.total == 0:
            return 0.0
        return (self.hits / self.total) * 100


@dataclass
class ErrorStats:
    """Error statistics by status code."""
    counts: Dict[int, int] = field(default_factory=dict)
    total_requests: int = 0
    
    def record_status(self, status_code: int) -> None:
        """Record a response status code."""
        self.total_requests += 1
        if status_code >= 400:
            self.counts[status_code] = self.counts.get(status_code, 0) + 1
    
    @property
    def error_rate(self) -> float:
        """5xx error rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        error_5xx = sum(v for k, v in self.counts.items() if 500 <= k < 600)
        return (error_5xx / self.total_requests) * 100


class MetricsCollector:
    """
    Singleton metrics collector for V2 API performance monitoring.
    
    Thread-safe for concurrent access from async handlers.
    """
    
    _instance: Optional["MetricsCollector"] = None
    
    def __new__(cls) -> "MetricsCollector":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        
        self._initialized = True
        self._lock = asyncio.Lock()
        
        # Per-endpoint latency tracking
        self.latency: Dict[str, LatencyStats] = {}
        self.latency["global"] = LatencyStats()
        
        # Cache statistics
        self.cache = CacheStats()
        
        # Error statistics
        self.errors = ErrorStats()
        
        # Circuit breaker state
        self.circuit_breaker_open = False
        self.circuit_breaker_trips = 0
        
        # Startup time
        self.start_time = time.time()
    
    async def record_request(
        self,
        endpoint: str,
        latency_ms: float,
        status_code: int,
        cache_hit: Optional[bool] = None,
    ) -> None:
        """Record metrics for a request (async version)."""
        async with self._lock:
            self._record_internal(endpoint, latency_ms, status_code, cache_hit)
    
    def record_request_sync(
        self,
        endpoint: str,
        latency_ms: float,
        status_code: int,
        cache_hit: Optional[bool] = None,
    ) -> None:
        """Record metrics for a request (sync version for middleware)."""
        self._record_internal(endpoint, latency_ms, status_code, cache_hit)
    
    def _record_internal(
        self,
        endpoint: str,
        latency_ms: float,
        status_code: int,
        cache_hit: Optional[bool] = None,
    ) -> None:
        """Internal method to record metrics."""
        # Latency
        if endpoint not in self.latency:
            self.latency[endpoint] = LatencyStats()
        self.latency[endpoint].record(latency_ms)
        self.latency["global"].record(latency_ms)
        
        # Errors
        self.errors.record_status(status_code)
        
        # Cache
        if cache_hit is True:
            self.cache.record_hit()
        elif cache_hit is False:
            self.cache.record_miss()
    
    async def record_circuit_breaker_trip(self) -> None:
        """Record a circuit breaker trip."""
        async with self._lock:
            self.circuit_breaker_open = True
            self.circuit_breaker_trips += 1
    
    async def record_circuit_breaker_reset(self) -> None:
        """Record circuit breaker reset."""
        async with self._lock:
            self.circuit_breaker_open = False
    
    def get_metrics(self) -> dict:
        """Get current metrics snapshot."""
        global_latency = self.latency.get("global", LatencyStats())
        
        # Per-endpoint latency
        endpoint_latency = {}
        for endpoint, stats in self.latency.items():
            if endpoint != "global" and stats.samples:
                endpoint_latency[endpoint] = {
                    "p50_ms": round(stats.percentile(50) or 0, 2),
                    "p95_ms": round(stats.percentile(95) or 0, 2),
                    "p99_ms": round(stats.percentile(99) or 0, 2),
                    "mean_ms": round(stats.mean() or 0, 2),
                    "samples": len(stats.samples),
                }
        
        return {
            "uptime_seconds": round(time.time() - self.start_time, 1),
            "latency": {
                "global": {
                    "p50_ms": round(global_latency.percentile(50) or 0, 2),
                    "p95_ms": round(global_latency.percentile(95) or 0, 2),
                    "p99_ms": round(global_latency.percentile(99) or 0, 2),
                    "mean_ms": round(global_latency.mean() or 0, 2),
                    "samples": len(global_latency.samples),
                },
                "by_endpoint": endpoint_latency,
            },
            "cache": {
                "hits": self.cache.hits,
                "misses": self.cache.misses,
                "total": self.cache.total,
                "hit_rate_percent": round(self.cache.hit_rate, 2),
            },
            "errors": {
                "total_requests": self.errors.total_requests,
                "error_counts": self.errors.counts,
                "error_rate_5xx_percent": round(self.errors.error_rate, 4),
            },
            "circuit_breaker": {
                "open": self.circuit_breaker_open,
                "total_trips": self.circuit_breaker_trips,
            },
            "targets": {
                "p50_target_ms": 30,
                "cache_hit_rate_target_percent": 90,
                "error_rate_target_percent": 0.1,
            },
            "status": self._compute_status(global_latency),
        }
    
    def _compute_status(self, latency: LatencyStats) -> dict:
        """Compute pass/fail status against targets."""
        p50 = latency.percentile(50) or 0
        cache_rate = self.cache.hit_rate
        error_rate = self.errors.error_rate
        
        return {
            "latency_ok": p50 < 30,
            "cache_ok": cache_rate >= 90 or self.cache.total < 100,  # Skip if not enough samples
            "errors_ok": error_rate < 0.1,
            "all_ok": (p50 < 30) and (cache_rate >= 90 or self.cache.total < 100) and (error_rate < 0.1),
        }


# Global instance
metrics = MetricsCollector()
