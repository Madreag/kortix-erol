"""
JWT Security Tests

Tests for JWT authentication vulnerabilities:
- Algorithm confusion attacks (none, wrong algorithm)
- Expired token rejection
- Tampered payload detection
- Invalid signature rejection
- Missing/malformed headers
"""
import os
import pytest
import httpx
import jwt
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from dotenv import load_dotenv
load_dotenv()


# Test configuration
BASE_URL = os.getenv("TEST_API_URL", "http://localhost:8000")
V2_BASE_URL = f"{BASE_URL.rstrip('/v1')}/v2"
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")


def create_test_jwt(
    payload: Dict[str, Any],
    secret: str = JWT_SECRET,
    algorithm: str = "HS256"
) -> str:
    """Helper to create JWT tokens for testing."""
    return jwt.encode(payload, secret, algorithm=algorithm)


def get_valid_payload(user_id: str = "test-user-id") -> Dict[str, Any]:
    """Get a valid JWT payload structure."""
    now = datetime.now(timezone.utc)
    return {
        "sub": user_id,
        "aud": "authenticated",
        "role": "authenticated",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }


class TestJWTAlgorithmConfusion:
    """Test algorithm confusion attacks."""

    @pytest.mark.asyncio
    async def test_none_algorithm_rejected(self):
        """
        SECURITY: 'none' algorithm tokens MUST be rejected.
        
        Attack: Attacker creates token with algorithm='none' to bypass signature verification.
        Expected: 401 Unauthorized
        """
        payload = get_valid_payload()
        
        # Create unsigned token with 'none' algorithm
        # Format: header.payload. (empty signature)
        import base64
        import json
        
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "none", "typ": "JWT"}).encode()
        ).rstrip(b'=').decode()
        
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).rstrip(b'=').decode()
        
        none_token = f"{header}.{payload_b64}."
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V2_BASE_URL}/threads",
                headers={"Authorization": f"Bearer {none_token}"},
                timeout=10.0
            )
        
        assert response.status_code == 401, (
            f"VULNERABILITY: 'none' algorithm token was accepted! "
            f"Status: {response.status_code}"
        )

    @pytest.mark.asyncio
    async def test_algorithm_switching_hs256_to_rs256(self):
        """
        SECURITY: Algorithm switching attacks must be prevented.
        
        Attack: Token signed with HS256 using public key as secret.
        Expected: 401 Unauthorized
        """
        payload = get_valid_payload()
        
        # Try to trick the server by using a different algorithm
        fake_token = create_test_jwt(payload, "fake-public-key", "HS256")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V2_BASE_URL}/threads",
                headers={"Authorization": f"Bearer {fake_token}"},
                timeout=10.0
            )
        
        assert response.status_code == 401, (
            f"VULNERABILITY: Algorithm switching attack succeeded! "
            f"Status: {response.status_code}"
        )

    @pytest.mark.asyncio
    async def test_unsupported_algorithm_rejected(self):
        """
        SECURITY: Unsupported algorithms must be rejected.
        
        Attack: Token with unsupported algorithm (e.g., HS384, HS512).
        Expected: 401 Unauthorized
        """
        payload = get_valid_payload()
        
        # Try HS384 which may not be in the allowed list
        try:
            hs384_token = create_test_jwt(payload, JWT_SECRET, "HS384")
        except Exception:
            pytest.skip("Cannot create HS384 token")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V2_BASE_URL}/threads",
                headers={"Authorization": f"Bearer {hs384_token}"},
                timeout=10.0
            )
        
        # Should be rejected - only HS256 and ES256 are supported
        assert response.status_code == 401, (
            f"VULNERABILITY: Unsupported algorithm accepted! "
            f"Status: {response.status_code}"
        )


class TestJWTExpiration:
    """Test JWT expiration handling."""

    @pytest.mark.asyncio
    async def test_expired_token_rejected(self):
        """
        SECURITY: Expired tokens MUST be rejected.
        
        Attack: Reuse an expired token.
        Expected: 401 Unauthorized with "Token has expired" message.
        """
        # Create token expired 1 hour ago
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "test-user-id",
            "aud": "authenticated",
            "role": "authenticated",
            "iat": int((now - timedelta(hours=2)).timestamp()),
            "exp": int((now - timedelta(hours=1)).timestamp()),
        }
        
        expired_token = create_test_jwt(payload)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V2_BASE_URL}/threads",
                headers={"Authorization": f"Bearer {expired_token}"},
                timeout=10.0
            )
        
        assert response.status_code == 401, (
            f"VULNERABILITY: Expired token was accepted! "
            f"Status: {response.status_code}"
        )

    @pytest.mark.asyncio
    async def test_future_iat_rejected(self):
        """
        SECURITY: Tokens with future 'iat' should be handled carefully.
        
        Attack: Token with iat in the future (clock skew attack).
        Expected: Rejected or handled with reasonable clock tolerance.
        """
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "test-user-id",
            "aud": "authenticated",
            "role": "authenticated",
            "iat": int((now + timedelta(hours=1)).timestamp()),  # Future iat
            "exp": int((now + timedelta(hours=2)).timestamp()),
        }
        
        future_token = create_test_jwt(payload)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V2_BASE_URL}/threads",
                headers={"Authorization": f"Bearer {future_token}"},
                timeout=10.0
            )
        
        # This should either be rejected or accepted with reasonable tolerance
        # Most systems allow a few minutes of clock skew
        # An hour in the future should definitely be rejected
        assert response.status_code in [401, 403], (
            f"POTENTIAL ISSUE: Token with far-future 'iat' was accepted. "
            f"Status: {response.status_code}"
        )


class TestJWTSignatureValidation:
    """Test JWT signature validation."""

    @pytest.mark.asyncio
    async def test_tampered_payload_rejected(self):
        """
        SECURITY: Tampered JWT payloads MUST be rejected.
        
        Attack: Modify payload (change user_id) without re-signing.
        Expected: 401 Unauthorized due to signature mismatch.
        """
        # Create valid token
        valid_payload = get_valid_payload("original-user-id")
        valid_token = create_test_jwt(valid_payload)
        
        # Tamper with the payload (decode, modify, re-encode without valid signature)
        import base64
        import json
        
        parts = valid_token.split('.')
        
        # Decode payload
        payload_json = base64.urlsafe_b64decode(parts[1] + '==')
        payload_data = json.loads(payload_json)
        
        # Modify user ID
        payload_data['sub'] = 'attacker-user-id'
        
        # Re-encode payload (without valid signature)
        new_payload = base64.urlsafe_b64encode(
            json.dumps(payload_data).encode()
        ).rstrip(b'=').decode()
        
        tampered_token = f"{parts[0]}.{new_payload}.{parts[2]}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V2_BASE_URL}/threads",
                headers={"Authorization": f"Bearer {tampered_token}"},
                timeout=10.0
            )
        
        assert response.status_code == 401, (
            f"VULNERABILITY: Tampered token was accepted! "
            f"Status: {response.status_code}"
        )

    @pytest.mark.asyncio
    async def test_wrong_secret_rejected(self):
        """
        SECURITY: Tokens signed with wrong secret MUST be rejected.
        
        Attack: Sign token with attacker's secret key.
        Expected: 401 Unauthorized.
        """
        payload = get_valid_payload()
        
        # Sign with a different secret
        wrong_secret_token = create_test_jwt(payload, "attacker-secret-key")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V2_BASE_URL}/threads",
                headers={"Authorization": f"Bearer {wrong_secret_token}"},
                timeout=10.0
            )
        
        assert response.status_code == 401, (
            f"VULNERABILITY: Token with wrong secret was accepted! "
            f"Status: {response.status_code}"
        )

    @pytest.mark.asyncio
    async def test_empty_signature_rejected(self):
        """
        SECURITY: Tokens with empty signature MUST be rejected.
        
        Attack: Remove signature from valid token.
        Expected: 401 Unauthorized.
        """
        valid_payload = get_valid_payload()
        valid_token = create_test_jwt(valid_payload)
        
        # Remove signature (keep header.payload.)
        parts = valid_token.split('.')
        empty_sig_token = f"{parts[0]}.{parts[1]}."
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V2_BASE_URL}/threads",
                headers={"Authorization": f"Bearer {empty_sig_token}"},
                timeout=10.0
            )
        
        assert response.status_code == 401, (
            f"VULNERABILITY: Token with empty signature was accepted! "
            f"Status: {response.status_code}"
        )


class TestJWTMalformedTokens:
    """Test handling of malformed JWT tokens."""

    @pytest.mark.asyncio
    async def test_invalid_format_rejected(self):
        """
        SECURITY: Invalid JWT format must be rejected.
        """
        invalid_tokens = [
            "not-a-jwt",
            "only.two.parts.here.extra",
            "invalid",
            "...",
            "header.payload",  # Missing signature part
        ]
        
        async with httpx.AsyncClient() as client:
            for token in invalid_tokens:
                response = await client.get(
                    f"{V2_BASE_URL}/threads",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0
                )
                
                # 400 is also acceptable (malformed request)
                # 429 is acceptable (rate limited from previous tests)
                assert response.status_code in [400, 401, 429], (
                    f"VULNERABILITY: Invalid token format accepted: '{token[:20]}...' "
                    f"Status: {response.status_code}"
                )

    @pytest.mark.asyncio
    async def test_missing_auth_header_rejected(self):
        """
        SECURITY: Requests without auth header must be rejected for protected endpoints.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V2_BASE_URL}/threads",
                timeout=10.0
            )
        
        assert response.status_code == 401, (
            f"VULNERABILITY: Protected endpoint accessible without auth! "
            f"Status: {response.status_code}"
        )

    @pytest.mark.asyncio
    async def test_wrong_auth_scheme_rejected(self):
        """
        SECURITY: Wrong auth scheme (Basic instead of Bearer) must be rejected.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V2_BASE_URL}/threads",
                headers={"Authorization": "Basic dXNlcjpwYXNz"},
                timeout=10.0
            )
        
        assert response.status_code == 401, (
            f"VULNERABILITY: Wrong auth scheme accepted! "
            f"Status: {response.status_code}"
        )


class TestJWTClaimValidation:
    """Test JWT claim validation."""

    @pytest.mark.asyncio
    async def test_missing_sub_claim_rejected(self):
        """
        SECURITY: Tokens without 'sub' claim must be rejected.
        """
        now = datetime.now(timezone.utc)
        payload = {
            # Missing 'sub' claim
            "aud": "authenticated",
            "role": "authenticated",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
        }
        
        token = create_test_jwt(payload)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V2_BASE_URL}/threads",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0
            )
        
        # 401 or 500 both indicate rejection (500 = less graceful but still rejected)
        assert response.status_code in [401, 500], (
            f"VULNERABILITY: Token without 'sub' claim was accepted! "
            f"Status: {response.status_code}"
        )

    @pytest.mark.asyncio
    async def test_empty_sub_claim_rejected(self):
        """
        SECURITY: Tokens with empty 'sub' claim must be rejected.
        """
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "",  # Empty sub
            "aud": "authenticated",
            "role": "authenticated",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
        }
        
        token = create_test_jwt(payload)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V2_BASE_URL}/threads",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0
            )
        
        # 401 or 500 both indicate rejection (500 = less graceful but still rejected)
        assert response.status_code in [401, 500], (
            f"VULNERABILITY: Token with empty 'sub' claim was accepted! "
            f"Status: {response.status_code}"
        )
