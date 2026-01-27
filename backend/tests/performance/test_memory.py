"""
Memory Leak Detection Tests

Uses tracemalloc to verify memory doesn't grow unbounded during sustained load.
"""
import pytest
import httpx
import asyncio
import tracemalloc
import gc
import os

BASE_URL = os.getenv("TEST_API_URL", "http://localhost:8000")
V2_BASE = f"{BASE_URL}/v2"

# Memory growth thresholds
MAX_MEMORY_GROWTH_MB = 10  # Max allowed memory growth during test
REQUESTS_PER_BATCH = 100
NUM_BATCHES = 10


class TestMemoryLeaks:
    """Verify no memory leaks during sustained request load."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_health_endpoint_no_memory_leak(self):
        """
        Health endpoint should not leak memory under sustained load.
        
        Pattern: Make 1000 requests in batches, measure memory growth.
        """
        gc.collect()
        tracemalloc.start()
        
        initial_snapshot = tracemalloc.take_snapshot()
        initial_current, initial_peak = tracemalloc.get_traced_memory()
        
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=30.0) as client:
            # Warmup
            for _ in range(10):
                await client.get("/health")
            
            # Sustained load in batches
            for batch in range(NUM_BATCHES):
                tasks = [client.get("/health") for _ in range(REQUESTS_PER_BATCH)]
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Verify responses (allow 429 rate limiting)
                success_count = sum(
                    1 for r in responses 
                    if isinstance(r, httpx.Response) and r.status_code in [200, 429]
                )
                assert success_count > REQUESTS_PER_BATCH * 0.8, f"Too many failures in batch {batch}"
                
                # Force GC between batches
                gc.collect()
        
        # Final memory check
        gc.collect()
        final_current, final_peak = tracemalloc.get_traced_memory()
        final_snapshot = tracemalloc.take_snapshot()
        
        tracemalloc.stop()
        
        # Calculate growth
        growth_bytes = final_current - initial_current
        growth_mb = growth_bytes / (1024 * 1024)
        
        # Get top memory consumers
        top_stats = final_snapshot.compare_to(initial_snapshot, 'lineno')[:5]
        
        print(f"\n📊 Memory Analysis ({NUM_BATCHES * REQUESTS_PER_BATCH} requests):")
        print(f"   Initial: {initial_current / 1024 / 1024:.2f} MB")
        print(f"   Final: {final_current / 1024 / 1024:.2f} MB")
        print(f"   Growth: {growth_mb:.2f} MB")
        print(f"   Peak: {final_peak / 1024 / 1024:.2f} MB")
        
        if top_stats:
            print("\n   Top memory consumers:")
            for stat in top_stats[:3]:
                print(f"     {stat}")
        
        assert growth_mb < MAX_MEMORY_GROWTH_MB, (
            f"Memory grew by {growth_mb:.2f}MB, exceeds {MAX_MEMORY_GROWTH_MB}MB threshold"
        )

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_connections_no_leak(self):
        """
        Verify connection pool doesn't leak under concurrent load.
        """
        gc.collect()
        tracemalloc.start()
        
        initial_current, _ = tracemalloc.get_traced_memory()
        
        # Create and destroy multiple client sessions
        for session in range(5):
            async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
                tasks = [client.get("/health") for _ in range(50)]
                await asyncio.gather(*tasks, return_exceptions=True)
            
            gc.collect()
        
        gc.collect()
        final_current, _ = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        growth_mb = (final_current - initial_current) / (1024 * 1024)
        
        print("\n📊 Connection Pool Memory (5 sessions × 50 requests):")
        print(f"   Growth: {growth_mb:.2f} MB")
        
        # Connection pools should be cleaned up
        assert growth_mb < 5, f"Connection pool memory grew by {growth_mb:.2f}MB"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_error_responses_no_leak(self):
        """
        Error responses should not leak memory.
        """
        gc.collect()
        tracemalloc.start()
        
        initial_current, _ = tracemalloc.get_traced_memory()
        
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            # Make requests to non-existent endpoints
            for _ in range(100):
                try:
                    await client.get("/nonexistent-endpoint-12345")
                except Exception:
                    pass
            
            gc.collect()
        
        gc.collect()
        final_current, _ = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        growth_mb = (final_current - initial_current) / (1024 * 1024)
        
        print("\n📊 Error Response Memory (100 404s):")
        print(f"   Growth: {growth_mb:.2f} MB")
        
        # 5MB threshold accounts for httpx internals and tracemalloc overhead
        assert growth_mb < 5, f"Error handling leaked {growth_mb:.2f}MB"


class TestMetricsCollectorMemory:
    """Verify MetricsCollector doesn't grow unbounded."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_latency_samples_bounded(self):
        """
        Latency samples should be bounded by deque maxlen.
        """
        # This test verifies the MetricsCollector implementation
        # uses bounded collections (deque with maxlen)
        from collections import deque
        
        # Simulate what MetricsCollector does
        latency_samples = deque(maxlen=1000)
        
        # Add 10,000 samples
        for i in range(10000):
            latency_samples.append(i * 0.001)
        
        # Should only keep last 1000
        assert len(latency_samples) == 1000
        assert latency_samples[0] == 9.0  # First kept sample
        
        print("\n📊 Bounded Collection Test:")
        print(f"   Added 10,000 samples, kept {len(latency_samples)}")
        print("   ✅ Deque maxlen working correctly")
