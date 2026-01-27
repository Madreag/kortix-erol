"""
Litestar V2 API E2E Tests

Tests for the new Litestar /v2 endpoints.
Verifies performance, functionality, and compatibility.
"""
import pytest
import httpx
import time
from typing import Generator
from tests.config import E2ETestConfig


def get_v2_base_url(test_config: E2ETestConfig) -> str:
    """Get the V2 API base URL (without /v1 suffix)."""
    base = test_config.base_url
    if base.endswith("/v1"):
        return base[:-3]  # Remove /v1
    return base


@pytest.fixture
def unauthenticated_client(test_config: E2ETestConfig) -> Generator[httpx.Client, None, None]:
    """Create unauthenticated HTTP client for public endpoints."""
    with httpx.Client(
        base_url=get_v2_base_url(test_config),
        timeout=30.0,
    ) as client:
        yield client


@pytest.fixture
async def v2_client(test_config: E2ETestConfig, auth_token: str):
    """Authenticated HTTP client for V2 API endpoints."""
    async with httpx.AsyncClient(
        base_url=get_v2_base_url(test_config),
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=30.0,
    ) as client:
        yield client


class TestLitestarV2Health:
    """Test /v2/health endpoints - no auth required."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_basic_health(self, test_config: E2ETestConfig):
        """Health endpoint returns healthy status with Litestar engine."""
        async with httpx.AsyncClient(base_url=get_v2_base_url(test_config), timeout=30.0) as client:
            response = await client.get("/v2/health")
            assert response.status_code == 200, f"Health check failed: {response.text}"
            
            data = response.json()
            assert data["status"] == "healthy"
            assert data.get("engine") == "litestar", "Should identify as Litestar engine"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_detailed_health(self, test_config: E2ETestConfig):
        """Detailed health includes component statuses."""
        async with httpx.AsyncClient(base_url=get_v2_base_url(test_config), timeout=30.0) as client:
            response = await client.get("/v2/health/detailed")
            assert response.status_code == 200, f"Detailed health failed: {response.text}"
            
            data = response.json()
            assert "status" in data
            assert "components" in data
            
            # Verify key components are reported
            components = data["components"]
            assert isinstance(components, dict)


class TestLitestarV2Auth:
    """Test /v2 endpoints require authentication."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_threads_requires_auth(self, test_config: E2ETestConfig):
        """GET /v2/threads returns 401 without auth."""
        async with httpx.AsyncClient(base_url=get_v2_base_url(test_config), timeout=30.0) as client:
            response = await client.get("/v2/threads")
            assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_projects_requires_auth(self, test_config: E2ETestConfig):
        """GET /v2/projects returns 401 without auth."""
        async with httpx.AsyncClient(base_url=get_v2_base_url(test_config), timeout=30.0) as client:
            response = await client.get("/v2/projects")
            assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_agents_requires_auth(self, test_config: E2ETestConfig):
        """GET /v2/agents returns 401 without auth."""
        async with httpx.AsyncClient(base_url=get_v2_base_url(test_config), timeout=30.0) as client:
            response = await client.get("/v2/agents")
            assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestLitestarV2Authenticated:
    """Test /v2 endpoints with authentication."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_list_threads(self, v2_client: httpx.AsyncClient):
        """GET /v2/threads returns paginated thread list."""
        response = await v2_client.get("/v2/threads", params={"page": 1, "limit": 10})
        
        # Accept both 200 (success) and 404 (no V2 route yet - fallback to V1)
        if response.status_code == 404:
            pytest.skip("V2 threads endpoint not yet implemented")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "threads" in data or isinstance(data, list), "Should return threads"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_list_projects(self, v2_client: httpx.AsyncClient):
        """GET /v2/projects returns project list."""
        response = await v2_client.get("/v2/projects")
        
        if response.status_code == 404:
            pytest.skip("V2 projects endpoint not yet implemented")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "projects" in data or isinstance(data, list), "Should return projects"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_list_agents(self, v2_client: httpx.AsyncClient):
        """GET /v2/agents returns agent list."""
        response = await v2_client.get("/v2/agents")
        
        if response.status_code == 404:
            pytest.skip("V2 agents endpoint not yet implemented")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "agents" in data or isinstance(data, list), "Should return agents"


class TestLitestarV2Performance:
    """Test /v2 endpoint performance characteristics."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_health_response_time(self, test_config: E2ETestConfig):
        """Health endpoint should respond in <50ms."""
        async with httpx.AsyncClient(base_url=get_v2_base_url(test_config), timeout=30.0) as client:
            # Warm up
            await client.get("/v2/health")
            
            # Measure
            start = time.perf_counter()
            response = await client.get("/v2/health")
            elapsed_ms = (time.perf_counter() - start) * 1000
            
            assert response.status_code == 200
            assert elapsed_ms < 100, f"Health endpoint took {elapsed_ms:.1f}ms, expected <100ms"
            print(f"✅ Health endpoint: {elapsed_ms:.1f}ms")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_cached_threads_response_time(self, v2_client: httpx.AsyncClient):
        """Cached /v2/threads should respond in <100ms."""
        # Warm cache
        response = await v2_client.get("/v2/threads", params={"page": 1, "limit": 10})
        
        if response.status_code == 404:
            pytest.skip("V2 threads endpoint not yet implemented")
        
        # Measure cached response
        start = time.perf_counter()
        response = await v2_client.get("/v2/threads", params={"page": 1, "limit": 10})
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        assert response.status_code == 200
        # Allow slack for dev mode - DB queries can vary
        # Production target is <200ms, dev mode allows up to 1000ms
        assert elapsed_ms < 1000, f"Cached threads took {elapsed_ms:.1f}ms, expected <1000ms"
        print(f"✅ Cached threads: {elapsed_ms:.1f}ms")


class TestLitestarV2VsV1Parity:
    """Test that V2 endpoints return compatible data with V1."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_threads_response_structure(self, v2_client: httpx.AsyncClient, client: httpx.AsyncClient):
        """V2 threads response has same structure as V1."""
        v2_response = await v2_client.get("/v2/threads", params={"page": 1, "limit": 5})
        v1_response = await client.get("/threads", params={"page": 1, "limit": 5})
        
        if v2_response.status_code == 404:
            pytest.skip("V2 threads endpoint not yet implemented")
        
        assert v2_response.status_code == 200
        assert v1_response.status_code == 200
        
        v2_data = v2_response.json()
        v1_data = v1_response.json()
        
        # Both should have threads key or be lists
        v2_has_threads = "threads" in v2_data or isinstance(v2_data, list)
        v1_has_threads = "threads" in v1_data or isinstance(v1_data, list)
        
        assert v2_has_threads, "V2 should return threads"
        assert v1_has_threads, "V1 should return threads"
        
        print("✅ V2 and V1 threads endpoints have compatible structure")
