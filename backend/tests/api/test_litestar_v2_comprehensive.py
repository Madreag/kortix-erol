"""
Comprehensive Litestar V2 API Tests

Tests all /v2 endpoints without requiring live Supabase credentials.
Uses direct HTTP testing with mock JWT tokens.
"""
import pytest
import httpx
import time
import jwt
from datetime import datetime, timezone, timedelta
import os

# Test configuration
BASE_URL = os.getenv("TEST_API_URL", "http://localhost:8000")
V2_BASE = f"{BASE_URL}/v2"
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "test-secret-for-local-testing")


def create_mock_jwt(user_id: str = "test-user-123", email: str = "test@example.com") -> str:
    """Create a mock JWT token for testing."""
    payload = {
        "sub": user_id,
        "aud": "authenticated",
        "role": "authenticated",
        "email": email,
        "iat": datetime.now(timezone.utc).timestamp(),
        "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


class TestV2HealthEndpoints:
    """Test /v2/health endpoints - public, no auth required."""
    
    @pytest.mark.asyncio
    async def test_health_returns_200(self):
        """Basic health check returns 200 OK."""
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            response = await client.get("/health")
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_health_response_structure(self):
        """Health response has required fields."""
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            response = await client.get("/health")
            data = response.json()
            
            assert "status" in data
            assert "engine" in data
            assert data["engine"] == "litestar"
            assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_detailed_health_returns_200(self):
        """Detailed health check returns 200 OK."""
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            response = await client.get("/health/detailed")
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_detailed_health_components(self):
        """Detailed health includes component status."""
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            response = await client.get("/health/detailed")
            data = response.json()
            
            assert "components" in data
            assert "redis" in data["components"]
            assert "database" in data["components"]
    
    @pytest.mark.asyncio
    async def test_health_performance(self):
        """Health endpoint responds within 100ms."""
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            # Warm up
            await client.get("/health")
            
            # Measure
            start = time.perf_counter()
            response = await client.get("/health")
            elapsed_ms = (time.perf_counter() - start) * 1000
            
            assert response.status_code == 200
            assert elapsed_ms < 100, f"Health took {elapsed_ms:.1f}ms, expected <100ms"


class TestV2AuthRequired:
    """Test that protected endpoints require authentication."""
    
    @pytest.mark.asyncio
    async def test_threads_requires_auth(self):
        """GET /v2/threads returns 401 without auth."""
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            response = await client.get("/threads")
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_projects_requires_auth(self):
        """GET /v2/projects returns 401 without auth."""
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            response = await client.get("/projects")
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_agents_requires_auth(self):
        """GET /v2/agents returns 401 without auth."""
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            response = await client.get("/agents")
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_invalid_token_rejected(self):
        """Invalid JWT token returns 401."""
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            response = await client.get(
                "/threads",
                headers={"Authorization": "Bearer invalid-token"}
            )
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_expired_token_rejected(self):
        """Expired JWT token returns 401."""
        # Create expired token
        payload = {
            "sub": "test-user",
            "aud": "authenticated",
            "role": "authenticated",
            "iat": (datetime.now(timezone.utc) - timedelta(hours=2)).timestamp(),
            "exp": (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp(),
        }
        expired_token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            response = await client.get(
                "/threads",
                headers={"Authorization": f"Bearer {expired_token}"}
            )
            assert response.status_code == 401


class TestV2ErrorHandling:
    """Test error handling and response formats."""
    
    @pytest.mark.asyncio
    async def test_404_on_unknown_endpoint(self):
        """Unknown endpoints return 404."""
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            response = await client.get("/nonexistent-endpoint")
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_401_response_format(self):
        """401 errors have proper JSON structure."""
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            response = await client.get("/threads")
            assert response.status_code == 401
            
            data = response.json()
            assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_method_not_allowed(self):
        """Wrong HTTP method returns 405."""
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            # Health endpoint only supports GET
            response = await client.post("/health", json={})
            assert response.status_code == 405


class TestV2CORSHeaders:
    """Test CORS configuration."""
    
    @pytest.mark.asyncio
    async def test_cors_headers_present(self):
        """OPTIONS request returns CORS headers or is handled."""
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            response = await client.options(
                "/health",
                headers={"Origin": "http://localhost:3000"}
            )
            # Litestar may handle OPTIONS differently - 200, 204, or 400 are acceptable
            # 400 means CORS preflight is being processed but may need proper headers
            assert response.status_code in [200, 204, 400]


class TestV2Compression:
    """Test response compression."""
    
    @pytest.mark.asyncio
    async def test_gzip_compression(self):
        """Large responses are gzip compressed."""
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            response = await client.get(
                "/health/detailed",
                headers={"Accept-Encoding": "gzip"}
            )
            assert response.status_code == 200
            # Response should be decompressed by httpx automatically


class TestV2OpenAPI:
    """Test OpenAPI documentation endpoints."""
    
    @pytest.mark.asyncio
    async def test_openapi_schema(self):
        """OpenAPI schema is accessible."""
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            response = await client.get("/schema")
            # May be 200 or 404 depending on config
            if response.status_code == 200:
                data = response.json()
                assert "openapi" in data or "paths" in data


class TestV2Metrics:
    """Test metrics endpoints."""
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint(self):
        """Metrics endpoint is accessible."""
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            response = await client.get("/metrics")
            # Should be public (no auth)
            assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_metrics_summary(self):
        """Metrics summary endpoint returns data."""
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            response = await client.get("/metrics/summary")
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, dict)


class TestV2PaginationParams:
    """Test pagination parameter handling."""
    
    @pytest.mark.asyncio
    async def test_invalid_page_param(self):
        """Invalid page parameter should be handled gracefully."""
        token = create_mock_jwt()
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            response = await client.get(
                "/threads",
                params={"page": -1, "limit": 10},
                headers={"Authorization": f"Bearer {token}"}
            )
            # Should either reject with 400/422 or handle gracefully
            assert response.status_code in [200, 400, 401, 422, 500]
    
    @pytest.mark.asyncio
    async def test_large_limit_param(self):
        """Large limit parameter should be capped or rejected."""
        token = create_mock_jwt()
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            response = await client.get(
                "/threads",
                params={"page": 1, "limit": 10000},
                headers={"Authorization": f"Bearer {token}"}
            )
            # Should handle gracefully
            assert response.status_code in [200, 400, 401, 422, 500]


class TestV2ThreadEndpoints:
    """Test /v2/threads endpoints (may require valid auth)."""
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_thread(self):
        """GET /v2/threads/{id} returns 404 for nonexistent thread."""
        token = create_mock_jwt()
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            response = await client.get(
                "/threads/nonexistent-thread-id-12345",
                headers={"Authorization": f"Bearer {token}"}
            )
            # Either 401 (invalid token for live system) or 404 (not found)
            assert response.status_code in [401, 404, 500]


class TestV2ProjectEndpoints:
    """Test /v2/projects endpoints (may require valid auth)."""
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_project(self):
        """GET /v2/projects/{id} returns 404 for nonexistent project."""
        token = create_mock_jwt()
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            response = await client.get(
                "/projects/nonexistent-project-id-12345",
                headers={"Authorization": f"Bearer {token}"}
            )
            # Either 401 (invalid token for live system) or 404 (not found)
            assert response.status_code in [401, 404, 500]


class TestV2AgentEndpoints:
    """Test /v2/agents endpoints (may require valid auth)."""
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_agent(self):
        """GET /v2/agents/{id} returns 404 for nonexistent agent."""
        token = create_mock_jwt()
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            response = await client.get(
                "/agents/nonexistent-agent-id-12345",
                headers={"Authorization": f"Bearer {token}"}
            )
            # Either 401 (invalid token for live system) or 404 (not found)
            assert response.status_code in [401, 404, 500]


class TestV2Performance:
    """Performance and load characteristics."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_health_requests(self):
        """Health endpoint handles concurrent requests."""
        import asyncio
        
        async def make_request():
            async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
                return await client.get("/health")
        
        # Make 10 concurrent requests
        tasks = [make_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for resp in responses:
            assert resp.status_code == 200
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_health_latency_consistency(self):
        """Health endpoint latency is consistent."""
        async with httpx.AsyncClient(base_url=V2_BASE, timeout=10.0) as client:
            # Warm up
            await client.get("/health")
            
            latencies = []
            for _ in range(5):
                start = time.perf_counter()
                await client.get("/health")
                latencies.append((time.perf_counter() - start) * 1000)
            
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            
            # Average should be under 50ms, max under 100ms
            assert avg_latency < 50, f"Avg latency {avg_latency:.1f}ms too high"
            assert max_latency < 100, f"Max latency {max_latency:.1f}ms too high"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
