"""
SDK V2 Compatibility Tests

Tests to verify the SDK correctly uses V2 endpoints with V1 fallback.

Run with: pytest tests/test_v2_compatibility.py -v
"""
import pytest
import sys
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

# Add SDK root to path for imports
SDK_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SDK_ROOT))


class TestKortixClientV2:
    """Test Kortix client V2 configuration."""
    
    def test_default_uses_v2(self):
        """Default client should use V2 endpoints."""
        from kortix.kortix import Kortix
        
        client = Kortix(api_key="test-key")
        assert client.is_using_v2 is True
        assert "/v2" in client.api_url
    
    def test_explicit_v1_mode(self):
        """Can explicitly disable V2."""
        from kortix.kortix import Kortix
        
        client = Kortix(api_key="test-key", use_v2=False)
        assert client.is_using_v2 is False
        assert "/v1" in client.api_url
    
    def test_v2_url_derivation(self):
        """V2 URL is correctly derived from V1 URL."""
        from kortix.kortix import Kortix
        
        client = Kortix(
            api_key="test-key",
            api_url="https://api.example.com/v1",
            use_v2=True,
        )
        assert client._api_url_v1 == "https://api.example.com/v1"
        assert client._api_url_v2 == "https://api.example.com/v2"


class TestThreadsClientV2:
    """Test ThreadsClient V2 fallback behavior."""
    
    def test_fallback_url_configured(self):
        """ThreadsClient accepts fallback_url parameter."""
        from kortix.api.threads import ThreadsClient
        
        client = ThreadsClient(
            base_url="https://api.example.com/v2",
            auth_token="test-token",
            fallback_url="https://api.example.com/v1",
        )
        
        assert client.base_url == "https://api.example.com/v2"
        assert client.fallback_url == "https://api.example.com/v1"
        assert client.fallback_client is not None
    
    def test_no_fallback_when_not_configured(self):
        """ThreadsClient works without fallback_url."""
        from kortix.api.threads import ThreadsClient
        
        client = ThreadsClient(
            base_url="https://api.example.com/v1",
            auth_token="test-token",
        )
        
        assert client.fallback_url is None
        assert client.fallback_client is None
    
    def test_circuit_breaker_initial_state(self):
        """Circuit breaker starts in closed state."""
        from kortix.api.threads import ThreadsClient
        
        client = ThreadsClient(
            base_url="https://api.example.com/v2",
            auth_token="test-token",
            fallback_url="https://api.example.com/v1",
        )
        
        assert client._v2_failure_count == 0
        assert client._v2_circuit_open is False


class TestAgentsClientV2:
    """Test AgentsClient V2 fallback behavior."""
    
    def test_fallback_url_configured(self):
        """AgentsClient accepts fallback_url parameter."""
        from kortix.api.agents import AgentsClient
        
        client = AgentsClient(
            base_url="https://api.example.com/v2",
            auth_token="test-token",
            fallback_url="https://api.example.com/v1",
        )
        
        assert client.base_url == "https://api.example.com/v2"
        assert client.fallback_url == "https://api.example.com/v1"
        assert client.fallback_client is not None
    
    def test_circuit_breaker_threshold(self):
        """Circuit breaker has correct threshold."""
        from kortix.api.agents import AgentsClient
        
        client = AgentsClient(
            base_url="https://api.example.com/v2",
            auth_token="test-token",
            fallback_url="https://api.example.com/v1",
        )
        
        assert client._v2_failure_threshold == 5


class TestCreateClientFunctions:
    """Test client factory functions."""
    
    def test_create_threads_client_with_fallback(self):
        """create_threads_client accepts fallback_url."""
        from kortix.api.threads import create_threads_client
        
        client = create_threads_client(
            base_url="https://api.example.com/v2",
            auth_token="test-token",
            fallback_url="https://api.example.com/v1",
        )
        
        assert client.fallback_url == "https://api.example.com/v1"
    
    def test_create_agents_client_with_fallback(self):
        """create_agents_client accepts fallback_url."""
        from kortix.api.agents import create_agents_client
        
        client = create_agents_client(
            base_url="https://api.example.com/v2",
            auth_token="test-token",
            fallback_url="https://api.example.com/v1",
        )
        
        assert client.fallback_url == "https://api.example.com/v1"


@pytest.mark.asyncio
class TestV2FallbackBehavior:
    """Test actual fallback behavior (requires mocking)."""
    
    async def test_success_resets_failure_count(self):
        """Successful request resets failure count."""
        from kortix.api.threads import ThreadsClient
        
        client = ThreadsClient(
            base_url="https://api.example.com/v2",
            auth_token="test-token",
            fallback_url="https://api.example.com/v1",
        )
        
        # Simulate some failures
        client._v2_failure_count = 3
        
        # Mock a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch.object(client.client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            response = await client._request_with_fallback("GET", "/threads")
            
            # Failure count should be reset
            assert client._v2_failure_count == 0
    
    async def test_circuit_opens_after_threshold(self):
        """Circuit opens after threshold failures."""
        from kortix.api.threads import ThreadsClient
        
        client = ThreadsClient(
            base_url="https://api.example.com/v2",
            auth_token="test-token",
            fallback_url="https://api.example.com/v1",
        )
        
        # Simulate reaching threshold
        client._v2_failure_count = client._v2_failure_threshold - 1
        
        # Mock a 500 error that triggers fallback
        mock_v2_response = MagicMock()
        mock_v2_response.status_code = 500
        mock_v2_response.request = MagicMock()
        
        mock_v1_response = MagicMock()
        mock_v1_response.status_code = 200
        
        with patch.object(client.client, 'request', new_callable=AsyncMock) as mock_v2:
            mock_v2.return_value = mock_v2_response
            
            with patch.object(client.fallback_client, 'request', new_callable=AsyncMock) as mock_v1:
                mock_v1.return_value = mock_v1_response
                
                # This should trigger circuit opening
                await client._request_with_fallback("GET", "/threads")
                
                # Circuit should now be open
                assert client._v2_circuit_open is True
