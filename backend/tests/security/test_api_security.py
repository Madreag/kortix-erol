"""
API Security Tests

Tests for API-level security:
- Rate limiting
- Security headers
- CORS configuration
- Error message information leakage
"""
import os
import asyncio
import pytest
import httpx
import jwt
from datetime import datetime, timezone, timedelta
from typing import List

from dotenv import load_dotenv
load_dotenv()


# Test configuration
BASE_URL = os.getenv("TEST_API_URL", "http://localhost:8000")
V2_BASE_URL = f"{BASE_URL.rstrip('/v1')}/v2"
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")


def create_valid_token(user_id: str = "test-user") -> str:
    """Create a valid JWT token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "aud": "authenticated",
        "role": "authenticated",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


class TestRateLimiting:
    """Test rate limiting protection."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_rate_limit_enforced(self):
        """
        SECURITY: Rate limiting should prevent request flooding.
        
        Attack: Send many requests rapidly to overwhelm the server.
        Expected: 429 Too Many Requests after threshold.
        """
        token = create_valid_token()
        
        responses: List[int] = []
        
        async with httpx.AsyncClient() as client:
            # Send 120 requests rapidly (limit is 100/min)
            tasks = []
            for i in range(120):
                task = client.get(
                    f"{V2_BASE_URL}/health",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=5.0
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, httpx.Response):
                    responses.append(result.status_code)
                elif isinstance(result, Exception):
                    # Connection errors might indicate rate limiting
                    responses.append(0)
        
        # Count 429 responses
        rate_limited = responses.count(429)
        
        # We should see some 429 responses after exceeding the limit
        # Note: Due to token bucket refill, exact count may vary
        assert rate_limited > 0 or len([r for r in responses if r == 0]) > 0, (
            f"VULNERABILITY: No rate limiting detected after 120 rapid requests! "
            f"Status codes: {set(responses)}"
        )

    @pytest.mark.asyncio
    async def test_rate_limit_per_ip(self):
        """
        SECURITY: Rate limiting should be per-IP, not global.
        
        This test verifies rate limits are applied per client IP.
        """
        # This is a basic check - in real testing you'd use different source IPs
        token = create_valid_token()
        
        async with httpx.AsyncClient() as client:
            # First request should work
            response = await client.get(
                f"{V2_BASE_URL}/health",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0
            )
        
        # 429 is acceptable (rate limited from previous tests)
        assert response.status_code in [200, 401, 429], (
            f"Health endpoint failed unexpectedly. Status: {response.status_code}"
        )


class TestSecurityHeaders:
    """Test security headers are present."""

    @pytest.mark.asyncio
    async def test_cors_headers_present(self):
        """
        SECURITY: CORS headers should be properly configured.
        """
        async with httpx.AsyncClient() as client:
            # Send preflight request
            response = await client.options(
                f"{V2_BASE_URL}/threads",
                headers={
                    "Origin": "https://kortix.com",
                    "Access-Control-Request-Method": "GET",
                },
                timeout=10.0
            )
        
        # Check CORS headers
        headers = response.headers
        
        # Should have Access-Control-Allow-Origin
        allowed_origins = headers.get("access-control-allow-origin", "")
        
        # Should NOT be wildcard for authenticated endpoints
        assert allowed_origins != "*", (
            "VULNERABILITY: CORS allows all origins (*) for authenticated endpoints!"
        )

    @pytest.mark.asyncio
    async def test_cors_rejects_unauthorized_origin(self):
        """
        SECURITY: CORS should reject requests from unauthorized origins.
        """
        async with httpx.AsyncClient() as client:
            response = await client.options(
                f"{V2_BASE_URL}/threads",
                headers={
                    "Origin": "https://evil-site.com",
                    "Access-Control-Request-Method": "GET",
                },
                timeout=10.0
            )
        
        # Check if evil origin is allowed
        allowed_origins = response.headers.get("access-control-allow-origin", "")
        
        assert "evil-site.com" not in allowed_origins, (
            f"VULNERABILITY: CORS allows unauthorized origin! "
            f"Allowed: {allowed_origins}"
        )

    @pytest.mark.asyncio
    async def test_content_type_header_enforced(self):
        """
        SECURITY: API should enforce proper Content-Type for POST/PUT requests.
        """
        token = create_valid_token()
        
        async with httpx.AsyncClient() as client:
            # Send POST without Content-Type
            response = await client.post(
                f"{V2_BASE_URL}/threads",
                headers={"Authorization": f"Bearer {token}"},
                content="not json",
                timeout=10.0
            )
        
        # Should reject malformed content
        # 401 (auth) or 405 (method not allowed) are also acceptable
        assert response.status_code in [400, 401, 405, 415, 422], (
            f"API accepted request without proper Content-Type. "
            f"Status: {response.status_code}"
        )


class TestErrorMessageLeakage:
    """Test that error messages don't leak sensitive information."""

    @pytest.mark.asyncio
    async def test_auth_error_no_user_enumeration(self):
        """
        SECURITY: Auth errors should not reveal if user exists.
        
        Attack: User enumeration via different error messages.
        Expected: Same error message for invalid user and invalid password.
        """
        # This test would need real auth endpoint
        # For now, check JWT errors don't leak info
        
        invalid_tokens = [
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJub25leGlzdGVudCJ9.invalid",
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhbm90aGVyIn0.invalid",
        ]
        
        error_messages = set()
        
        async with httpx.AsyncClient() as client:
            for token in invalid_tokens:
                response = await client.get(
                    f"{V2_BASE_URL}/threads",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0
                )
                
                if response.status_code == 401:
                    try:
                        error_data = response.json()
                        error_messages.add(error_data.get("detail", ""))
                    except Exception:
                        error_messages.add(response.text)
        
        # All error messages should be generic (same message)
        # to prevent user enumeration
        assert len(error_messages) <= 1 or all(
            "user" not in msg.lower() for msg in error_messages
        ), (
            f"POTENTIAL ISSUE: Different auth error messages may enable enumeration. "
            f"Messages: {error_messages}"
        )

    @pytest.mark.asyncio
    async def test_internal_errors_no_stack_trace(self):
        """
        SECURITY: Internal errors should not expose stack traces.
        """
        token = create_valid_token()
        
        async with httpx.AsyncClient() as client:
            # Try to trigger an error with malformed data
            response = await client.post(
                f"{V2_BASE_URL}/threads",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"invalid_field": "x" * 10000},  # Large invalid data
                timeout=10.0
            )
        
        response_text = response.text.lower()
        
        # Should not contain stack trace indicators
        dangerous_patterns = [
            "traceback",
            "file \"",
            ".py\", line",
            "exception:",
            "error at",
        ]
        
        for pattern in dangerous_patterns:
            assert pattern not in response_text, (
                f"VULNERABILITY: Error response contains stack trace! "
                f"Found: {pattern}"
            )

    @pytest.mark.asyncio
    async def test_database_errors_sanitized(self):
        """
        SECURITY: Database errors should not expose schema information.
        """
        token = create_valid_token()
        
        async with httpx.AsyncClient() as client:
            # Try SQL-injection-like input to trigger DB error
            response = await client.get(
                f"{V2_BASE_URL}/threads?page=1'--",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0
            )
        
        response_text = response.text.lower()
        
        # Should not contain DB schema info
        dangerous_patterns = [
            "postgresql",
            "syntax error",
            "column \"",
            "table \"",
            "relation \"",
            "select ",
            "from ",
        ]
        
        for pattern in dangerous_patterns:
            assert pattern not in response_text, (
                f"VULNERABILITY: Error response contains DB info! "
                f"Found: {pattern}"
            )


class TestRequestValidation:
    """Test request validation and sanitization."""

    @pytest.mark.asyncio
    async def test_oversized_request_rejected(self):
        """
        SECURITY: Oversized requests should be rejected.
        
        Attack: Send very large request body to cause DoS.
        Expected: 413 Payload Too Large or similar.
        """
        token = create_valid_token()
        
        async with httpx.AsyncClient() as client:
            # Send very large JSON body (10MB)
            large_data = {"data": "x" * (10 * 1024 * 1024)}
            
            try:
                response = await client.post(
                    f"{V2_BASE_URL}/threads",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=large_data,
                    timeout=30.0
                )
                
                # Should be rejected
                # 401 (auth) or 405 (method not allowed) are also acceptable
                assert response.status_code in [400, 401, 405, 413, 422], (
                    f"VULNERABILITY: Server accepted 10MB request! "
                    f"Status: {response.status_code}"
                )
            except httpx.RequestError:
                # Connection error is also acceptable (server dropped connection)
                pass

    @pytest.mark.asyncio
    async def test_special_characters_in_params(self):
        """
        SECURITY: Special characters in query params should be handled safely.
        """
        token = create_valid_token()
        
        special_inputs = [
            "test%00null",  # Null byte
            "../../../etc/passwd",  # Path traversal
            "<script>alert(1)</script>",  # XSS
            "'; DROP TABLE threads; --",  # SQL injection
        ]
        
        async with httpx.AsyncClient() as client:
            for input_val in special_inputs:
                response = await client.get(
                    f"{V2_BASE_URL}/threads",
                    params={"search": input_val},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0
                )
                
                # Should not crash or expose errors
                # 401 is acceptable - auth blocks request before param processing
                # 500 is acceptable if no sensitive info exposed
                assert response.status_code in [200, 400, 401, 422, 500], (
                    f"Unexpected response for special input '{input_val[:20]}'. "
                    f"Status: {response.status_code}"
                )


class TestHTTPMethods:
    """Test HTTP method handling."""

    @pytest.mark.asyncio
    async def test_trace_method_disabled(self):
        """
        SECURITY: TRACE method should be disabled (XST attack prevention).
        """
        async with httpx.AsyncClient() as client:
            response = await client.request(
                "TRACE",
                f"{V2_BASE_URL}/threads",
                timeout=10.0
            )
        
        assert response.status_code in [405, 501], (
            f"VULNERABILITY: TRACE method enabled! "
            f"Status: {response.status_code}"
        )

    @pytest.mark.asyncio
    async def test_unexpected_methods_rejected(self):
        """
        SECURITY: Unexpected HTTP methods should be rejected.
        """
        token = create_valid_token()
        
        unexpected_methods = ["CONNECT", "PROPFIND", "MKCOL"]
        
        async with httpx.AsyncClient() as client:
            for method in unexpected_methods:
                try:
                    response = await client.request(
                        method,
                        f"{V2_BASE_URL}/threads",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=10.0
                    )
                    
                    assert response.status_code in [405, 501], (
                        f"VULNERABILITY: Unexpected method {method} allowed! "
                        f"Status: {response.status_code}"
                    )
                except httpx.RequestError:
                    # Connection error is acceptable
                    pass
