"""
Performance and Load Tests for Litestar V2 API

Tests latency, throughput, and concurrent request handling.
"""
import pytest
import httpx
import time
import asyncio
import statistics
import os

BASE_URL = os.getenv("TEST_API_URL", "http://localhost:8000")
V2_BASE = f"{BASE_URL}/v2"


class TestLatencyTargets:
    """Test that endpoints meet latency targets."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_health_latency_target(self):
        """Health endpoint: <50ms target."""
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            # Warmup
            for _ in range(3):
                await client.get("/health")
            
            latencies = []
            for _ in range(10):
                start = time.perf_counter()
                response = await client.get("/health")
                latency_ms = (time.perf_counter() - start) * 1000
                latencies.append(latency_ms)
                # 429 is acceptable (rate limited)
                assert response.status_code in [200, 429], f"Unexpected status: {response.status_code}"
            
            avg = statistics.mean(latencies)
            sorted_latencies = sorted(latencies)
            p95 = sorted_latencies[int(len(latencies) * 0.95)]
            p99 = sorted_latencies[int(len(latencies) * 0.99)] if len(latencies) >= 100 else max(latencies)
            
            print("\n📊 Health Endpoint Latency:")
            print(f"   Avg: {avg:.1f}ms | P95: {p95:.1f}ms | P99: {p99:.1f}ms | Min: {min(latencies):.1f}ms | Max: {max(latencies):.1f}ms")
            
            assert avg < 50, f"Avg latency {avg:.1f}ms exceeds 50ms target"
            assert p95 < 100, f"P95 latency {p95:.1f}ms exceeds 100ms target"
            assert p99 < 200, f"P99 latency {p99:.1f}ms exceeds 200ms target"
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_detailed_health_latency(self):
        """Detailed health (includes Redis ping): <100ms target."""
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            # Warmup
            for _ in range(3):
                await client.get("/health/detailed")
            
            latencies = []
            for _ in range(10):
                start = time.perf_counter()
                response = await client.get("/health/detailed")
                latency_ms = (time.perf_counter() - start) * 1000
                latencies.append(latency_ms)
                assert response.status_code == 200
            
            avg = statistics.mean(latencies)
            sorted_latencies = sorted(latencies)
            p95 = sorted_latencies[int(len(latencies) * 0.95)]
            p99 = sorted_latencies[int(len(latencies) * 0.99)] if len(latencies) >= 100 else max(latencies)
            
            print("\n📊 Detailed Health Latency:")
            print(f"   Avg: {avg:.1f}ms | P95: {p95:.1f}ms | P99: {p99:.1f}ms | Min: {min(latencies):.1f}ms | Max: {max(latencies):.1f}ms")
            
            assert avg < 100, f"Avg latency {avg:.1f}ms exceeds 100ms target"
            assert p95 < 200, f"P95 latency {p95:.1f}ms exceeds 200ms target"
            assert p99 < 500, f"P99 latency {p99:.1f}ms exceeds 500ms target"


class TestThroughput:
    """Test request throughput."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_health_throughput(self):
        """Health endpoint should handle 100+ requests/second."""
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=30.0) as client:
            # Warmup
            await client.get("/health")
            
            num_requests = 100
            start = time.perf_counter()
            
            tasks = [client.get("/health") for _ in range(num_requests)]
            responses = await asyncio.gather(*tasks)
            
            elapsed = time.perf_counter() - start
            rps = num_requests / elapsed
            
            # Count 200 (success) and 429 (rate limited - expected)
            success_count = sum(1 for r in responses if r.status_code == 200)
            rate_limited = sum(1 for r in responses if r.status_code == 429)
            
            print("\n📊 Health Throughput Test:")
            print(f"   Requests: {num_requests} | Time: {elapsed:.2f}s | RPS: {rps:.0f}")
            print(f"   Success: {success_count}/{num_requests} | Rate Limited: {rate_limited}")
            
            # Rate limiting is expected behavior at 100 req/min
            # Test passes if all responses are either 200 or 429
            valid_count = success_count + rate_limited
            assert valid_count == num_requests, f"Only {valid_count}/{num_requests} valid responses"
            assert rps > 50, f"Throughput {rps:.0f} RPS below 50 RPS target"


class TestConcurrency:
    """Test concurrent request handling."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_health_requests(self):
        """Handle 50 concurrent health requests."""
        num_concurrent = 50
        
        async def make_request():
            async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
                start = time.perf_counter()
                response = await client.get("/health")
                latency = (time.perf_counter() - start) * 1000
                return response.status_code, latency
        
        start = time.perf_counter()
        results = await asyncio.gather(*[make_request() for _ in range(num_concurrent)])
        total_time = time.perf_counter() - start
        
        statuses = [r[0] for r in results]
        latencies = [r[1] for r in results]
        
        success_count = statuses.count(200)
        rate_limited = statuses.count(429)
        avg_latency = statistics.mean(latencies)
        max_latency = max(latencies)
        
        print(f"\n📊 Concurrent Requests Test ({num_concurrent} concurrent):")
        print(f"   Total time: {total_time:.2f}s | Success: {success_count}/{num_concurrent}")
        print(f"   Rate Limited: {rate_limited} | Avg latency: {avg_latency:.1f}ms | Max latency: {max_latency:.1f}ms")
        
        # Rate limiting is expected behavior at 100 req/min
        valid_count = success_count + rate_limited
        assert valid_count == num_concurrent, f"Only {valid_count}/{num_concurrent} valid responses"
        assert avg_latency < 500, f"Avg latency {avg_latency:.1f}ms too high under load"
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_burst_requests(self):
        """Handle burst of 20 rapid requests."""
        num_requests = 20
        
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            # Warmup
            await client.get("/health")
            
            # Burst
            start = time.perf_counter()
            tasks = [client.get("/health") for _ in range(num_requests)]
            responses = await asyncio.gather(*tasks)
            elapsed = time.perf_counter() - start
            
            success_count = sum(1 for r in responses if r.status_code == 200)
            rate_limited = sum(1 for r in responses if r.status_code == 429)
            
            print(f"\n📊 Burst Test ({num_requests} requests):")
            print(f"   Total time: {elapsed:.3f}s | Success: {success_count}/{num_requests}")
            print(f"   Rate Limited: {rate_limited}")
            
            # Rate limiting is expected behavior
            valid_count = success_count + rate_limited
            assert valid_count == num_requests, f"Only {valid_count}/{num_requests} valid responses"


class TestStress:
    """Stress testing for edge cases."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_sustained_load(self):
        """Sustain load for 5 seconds."""
        duration_seconds = 5
        
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            start = time.perf_counter()
            request_count = 0
            errors = 0
            
            rate_limited = 0
            
            while (time.perf_counter() - start) < duration_seconds:
                try:
                    response = await client.get("/health")
                    if response.status_code == 200:
                        request_count += 1
                    elif response.status_code == 429:
                        rate_limited += 1
                    else:
                        errors += 1
                except Exception:
                    errors += 1
            
            elapsed = time.perf_counter() - start
            rps = request_count / elapsed
            
            total_requests = request_count + rate_limited
            total_rps = total_requests / elapsed
            
            print(f"\n📊 Sustained Load Test ({duration_seconds}s):")
            print(f"   Success: {request_count} | Rate Limited: {rate_limited} | Errors: {errors}")
            print(f"   Total RPS: {total_rps:.0f} | Effective RPS: {rps:.0f}")
            
            # Rate limiting (429) is expected behavior, not an error
            # Total RPS (including rate limited) should be high
            assert errors == 0, f"{errors} unexpected errors during sustained load"
            assert total_rps > 10, f"Total RPS {total_rps:.0f} below minimum"


class TestResponseSizes:
    """Test response size characteristics."""
    
    @pytest.mark.asyncio
    async def test_health_response_size(self):
        """Health response should be compact."""
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            response = await client.get("/health")
            size_bytes = len(response.content)
            
            print(f"\n📊 Health Response Size: {size_bytes} bytes")
            
            # Health response should be under 500 bytes
            assert size_bytes < 500, f"Health response {size_bytes} bytes exceeds 500 byte target"
    
    @pytest.mark.asyncio
    async def test_detailed_health_response_size(self):
        """Detailed health response should be under 1KB."""
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            response = await client.get("/health/detailed")
            size_bytes = len(response.content)
            
            print(f"\n📊 Detailed Health Response Size: {size_bytes} bytes")
            
            assert size_bytes < 1024, f"Detailed health {size_bytes} bytes exceeds 1KB target"


class TestErrorRecovery:
    """Test error handling under load."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_invalid_endpoint_flood(self):
        """System handles flood of invalid requests gracefully."""
        num_requests = 20
        
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            start = time.perf_counter()
            tasks = [client.get("/nonexistent") for _ in range(num_requests)]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = time.perf_counter() - start
            
            # Count 404s (expected) vs other errors
            not_found = sum(1 for r in responses if isinstance(r, httpx.Response) and r.status_code == 404)
            
            print("\n📊 Invalid Endpoint Flood Test:")
            print(f"   Requests: {num_requests} | 404s: {not_found} | Time: {elapsed:.2f}s")
            
            assert not_found == num_requests, "All invalid requests should return 404"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
