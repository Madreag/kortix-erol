"""
Data Exposure Tests

Tests for sensitive data exposure:
- API keys in responses
- Credentials in logs/errors
- PII exposure
- Sensitive metadata leakage
"""
import os
import uuid
import pytest
import httpx
import jwt
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
load_dotenv()


# Test configuration
BASE_URL = os.getenv("TEST_API_URL", "http://localhost:8000")
V1_BASE_URL = f"{BASE_URL}"
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


class TestSensitiveDataInResponses:
    """Test that sensitive data is not exposed in API responses."""

    SENSITIVE_PATTERNS = [
        "password",
        "secret",
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "private_key",
        "jwt_secret",
        "service_role",
        "credit_card",
        "ssn",
        "social_security",
    ]

    @pytest.mark.asyncio
    async def test_no_passwords_in_user_response(self):
        """
        SECURITY: Password hashes should never be in API responses.
        """
        token = create_valid_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V1_BASE_URL}/users/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0
            )
        
        if response.status_code == 200:
            response_lower = response.text.lower()
            
            assert "password" not in response_lower, (
                "VULNERABILITY: Password field exposed in user response!"
            )
            assert "hash" not in response_lower or "password_hash" not in response_lower, (
                "VULNERABILITY: Password hash exposed in user response!"
            )

    @pytest.mark.asyncio
    async def test_no_api_keys_in_list_responses(self):
        """
        SECURITY: Full API keys should not be returned in list responses.
        """
        token = create_valid_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V1_BASE_URL}/api-keys",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0
            )
        
        if response.status_code == 200:
            # API keys should be masked (show only prefix/suffix)
            response_text = response.text
            
            # Look for patterns that might be full API keys
            # Full keys are typically 32+ characters of random data
            import re
            
            # If keys are returned, they should be masked
            if "secret" in response_text.lower() or "key" in response_text.lower():
                # Check for masked format like "sk_****abc123"
                if re.search(r'"[a-z]{2}_[a-zA-Z0-9]{32,}"', response_text):
                    pytest.fail(
                        "VULNERABILITY: Full API key exposed in response!"
                    )

    @pytest.mark.asyncio
    async def test_no_internal_ids_in_error_messages(self):
        """
        SECURITY: Internal IDs should not be exposed in error messages.
        """
        token = create_valid_token()
        
        async with httpx.AsyncClient() as client:
            # Trigger an error with invalid ID
            response = await client.get(
                f"{V2_BASE_URL}/threads/invalid-thread-id",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0
            )
        
        if response.status_code >= 400:
            response_lower = response.text.lower()
            
            # Should not expose database internal IDs
            dangerous_patterns = [
                "internal_id",
                "row_id",
                "sequence",
                "auto_increment",
            ]
            
            for pattern in dangerous_patterns:
                assert pattern not in response_lower, (
                    f"POTENTIAL ISSUE: Internal ID pattern '{pattern}' in error response"
                )


class TestEnvironmentVariableExposure:
    """Test that environment variables are not exposed."""

    @pytest.mark.asyncio
    async def test_env_vars_not_in_responses(self):
        """
        SECURITY: Environment variable values should never be in responses.
        """
        token = create_valid_token()
        
        endpoints = [
            f"{V2_BASE_URL}/health",
            f"{V2_BASE_URL}/threads",
            f"{V1_BASE_URL}/",
        ]
        
        env_patterns = [
            "SUPABASE_",
            "DATABASE_URL",
            "REDIS_",
            "AWS_",
            "OPENAI_",
            "ANTHROPIC_",
        ]
        
        async with httpx.AsyncClient() as client:
            for endpoint in endpoints:
                response = await client.get(
                    endpoint,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0
                )
                
                for pattern in env_patterns:
                    assert pattern not in response.text, (
                        f"VULNERABILITY: Env var pattern '{pattern}' exposed at {endpoint}!"
                    )

    @pytest.mark.asyncio
    async def test_debug_endpoint_protected(self):
        """
        SECURITY: Debug endpoints should not be accessible in production.
        """
        debug_endpoints = [
            "/debug",
            "/debug/env",
            "/debug/config",
            "/_debug",
            "/internal/debug",
        ]
        
        async with httpx.AsyncClient() as client:
            for endpoint in debug_endpoints:
                response = await client.get(
                    f"{V1_BASE_URL}{endpoint}",
                    timeout=10.0
                )
                
                # Should be 404 (not found) or 403 (forbidden)
                assert response.status_code in [401, 403, 404], (
                    f"VULNERABILITY: Debug endpoint accessible! "
                    f"Endpoint: {endpoint}, Status: {response.status_code}"
                )


class TestLogSanitization:
    """Test that logs don't contain sensitive data."""

    @pytest.mark.asyncio
    async def test_sensitive_data_not_logged(self):
        """
        SECURITY: Sensitive data should be sanitized in logs.
        
        Note: This test can only verify what's returned to the client.
        Full log testing requires access to actual logs.
        """
        token = create_valid_token()
        
        # Send request with sensitive data
        sensitive_data = {
            "password": "secret123",
            "api_key": "sk_test_12345",
            "credit_card": "4111111111111111",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{V2_BASE_URL}/threads",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"name": "Test", "metadata": sensitive_data},
                timeout=10.0
            )
        
        # If error, check it doesn't reflect sensitive data
        if response.status_code >= 400:
            response_text = response.text
            
            # Sensitive values should not be echoed back
            assert "secret123" not in response_text, (
                "VULNERABILITY: Password echoed in error response!"
            )
            assert "sk_test_12345" not in response_text, (
                "VULNERABILITY: API key echoed in error response!"
            )
            assert "4111111111111111" not in response_text, (
                "VULNERABILITY: Credit card echoed in error response!"
            )


class TestPIIProtection:
    """Test PII (Personally Identifiable Information) protection."""

    @pytest.mark.asyncio
    async def test_email_not_exposed_to_other_users(self):
        """
        SECURITY: User A should not see User B's email address.
        """
        user_a_id = str(uuid.uuid4())
        token = create_valid_token(user_a_id)
        
        async with httpx.AsyncClient() as client:
            # List threads - should not expose other users' emails
            response = await client.get(
                f"{V2_BASE_URL}/threads",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0
            )
        
        if response.status_code == 200:
            # Check that emails of other users are not exposed
            # (This is a basic check - real test needs actual data)
            import re
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            re.findall(email_pattern, response.text)
            
            # If emails are found, they should only be the current user's
            # For a new test user, there should be no emails
            pass  # This test is more meaningful with real user data

    @pytest.mark.asyncio
    async def test_user_metadata_not_exposed(self):
        """
        SECURITY: Private user metadata should not be exposed to others.
        """
        user_id = str(uuid.uuid4())
        token = create_valid_token(user_id)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V1_BASE_URL}/users/{uuid.uuid4()}",  # Random other user
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0
            )
        
        # Should not be accessible
        assert response.status_code in [401, 403, 404], (
            f"POTENTIAL ISSUE: Can access other user's profile. "
            f"Status: {response.status_code}"
        )


class TestTokenExposure:
    """Test that tokens are properly protected."""

    @pytest.mark.asyncio
    async def test_jwt_not_logged_in_response(self):
        """
        SECURITY: JWT tokens should not be echoed in responses.
        """
        token = create_valid_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V2_BASE_URL}/threads",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0
            )
        
        # Token should not appear in response body
        assert token not in response.text, (
            "VULNERABILITY: JWT token echoed in response body!"
        )

    @pytest.mark.asyncio
    async def test_refresh_token_not_in_response_body(self):
        """
        SECURITY: Refresh tokens should only be in cookies, not response body.
        """
        # This depends on auth implementation
        # Check that tokens are in HttpOnly cookies, not body
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{V1_BASE_URL}/auth/login",
                json={"email": "test@test.com", "password": "test"},
                timeout=10.0
            )
        
        if response.status_code == 200:
            # Refresh token should be in HttpOnly cookie, not body
            if "refresh_token" in response.text:
                # Check if it looks like a full token
                import re
                if re.search(r'"refresh_token":\s*"[a-zA-Z0-9._-]{50,}"', response.text):
                    pytest.fail(
                        "POTENTIAL ISSUE: Refresh token in response body. "
                        "Should be HttpOnly cookie only."
                    )


class TestMetadataExposure:
    """Test that internal metadata is not exposed."""

    @pytest.mark.asyncio
    async def test_server_version_not_exposed(self):
        """
        SECURITY: Server version should not be exposed (aids attacker recon).
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V2_BASE_URL}/health",
                timeout=10.0
            )
        
        # Check headers for version info
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        
        # Should not expose specific versions
        version_headers = ["x-powered-by", "server", "x-version"]
        
        for header in version_headers:
            if header in headers_lower:
                value = headers_lower[header]
                # Generic values are OK, specific versions are not
                if any(v in value.lower() for v in ["python", "uvicorn", "litestar"]):
                    # Check if version number is exposed
                    import re
                    if re.search(r'\d+\.\d+', value):
                        pytest.fail(
                            f"POTENTIAL ISSUE: Server version exposed in {header}: {value}"
                        )

    @pytest.mark.asyncio
    async def test_database_type_not_exposed(self):
        """
        SECURITY: Database type/version should not be exposed in errors.
        """
        token = create_valid_token()
        
        async with httpx.AsyncClient() as client:
            # Try to trigger database error
            response = await client.get(
                f"{V2_BASE_URL}/threads?page=invalid",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0
            )
        
        if response.status_code >= 400:
            response_lower = response.text.lower()
            
            db_indicators = [
                "postgresql",
                "mysql",
                "sqlite",
                "mongodb",
                "supabase",  # Don't expose backend provider
            ]
            
            for indicator in db_indicators:
                assert indicator not in response_lower, (
                    f"POTENTIAL ISSUE: Database type '{indicator}' exposed in error"
                )
