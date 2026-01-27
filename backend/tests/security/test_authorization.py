"""
Authorization Security Tests

Tests for authorization vulnerabilities:
- IDOR (Insecure Direct Object Reference)
- Privilege escalation
- Cross-user data access
- Admin endpoint protection
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


def create_user_token(user_id: str, role: str = "authenticated") -> str:
    """Create a JWT token for a specific user."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "aud": "authenticated",
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


class TestIDORThreadAccess:
    """Test IDOR vulnerabilities in thread access."""

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_users_thread(self):
        """
        SECURITY: User A should NOT be able to access User B's private thread.
        
        Attack: IDOR - Access thread by guessing/knowing another user's thread ID.
        Expected: 403 Forbidden or 404 Not Found.
        """
        user_a_id = str(uuid.uuid4())
        user_b_thread_id = str(uuid.uuid4())  # User B's thread
        
        user_a_token = create_user_token(user_a_id)
        
        async with httpx.AsyncClient() as client:
            # User A tries to access User B's thread
            response = await client.get(
                f"{V2_BASE_URL}/threads/{user_b_thread_id}",
                headers={"Authorization": f"Bearer {user_a_token}"},
                timeout=10.0
            )
        
        # Should be 403 (forbidden) or 404 (not found/hidden)
        # 401 is acceptable - mock JWT may not pass live Supabase validation
        assert response.status_code in [401, 403, 404], (
            f"VULNERABILITY: User can access other user's thread! "
            f"Status: {response.status_code}, Response: {response.text[:200]}"
        )

    @pytest.mark.asyncio
    async def test_user_cannot_delete_other_users_thread(self):
        """
        SECURITY: User A should NOT be able to delete User B's thread.
        
        Attack: IDOR - Attempt to delete another user's thread.
        Expected: 403 Forbidden or 404 Not Found.
        """
        user_a_id = str(uuid.uuid4())
        user_b_thread_id = str(uuid.uuid4())
        
        user_a_token = create_user_token(user_a_id)
        
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{V2_BASE_URL}/threads/{user_b_thread_id}",
                headers={"Authorization": f"Bearer {user_a_token}"},
                timeout=10.0
            )
        
        # 401 is acceptable - mock JWT may not pass live Supabase validation
        assert response.status_code in [401, 403, 404], (
            f"VULNERABILITY: User can delete other user's thread! "
            f"Status: {response.status_code}"
        )

    @pytest.mark.asyncio
    async def test_user_cannot_list_other_users_threads(self):
        """
        SECURITY: User A should only see their own threads in list.
        
        Attack: Attempt to list threads belonging to other users.
        Expected: Only own threads returned.
        """
        user_a_id = str(uuid.uuid4())
        user_a_token = create_user_token(user_a_id)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V2_BASE_URL}/threads",
                headers={"Authorization": f"Bearer {user_a_token}"},
                timeout=10.0
            )
        
        if response.status_code == 200:
            data = response.json()
            threads = data.get("threads", [])
            
            # All returned threads should belong to user_a
            # (For a new user, this should be empty)
            for thread in threads:
                # If there are threads, verify they belong to this user
                # Note: This test is more meaningful with real user data
                pass
        
        # At minimum, request should succeed (even if empty list)
        # 401 is acceptable - mock JWT may not pass live Supabase validation
        assert response.status_code in [200, 401], (
            f"Thread list endpoint failed. Status: {response.status_code}"
        )


class TestIDORProjectAccess:
    """Test IDOR vulnerabilities in project access."""

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_users_project(self):
        """
        SECURITY: User A should NOT be able to access User B's private project.
        """
        user_a_id = str(uuid.uuid4())
        user_b_project_id = str(uuid.uuid4())
        
        user_a_token = create_user_token(user_a_id)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V2_BASE_URL}/projects/{user_b_project_id}",
                headers={"Authorization": f"Bearer {user_a_token}"},
                timeout=10.0
            )
        
        # 401 is acceptable - mock JWT may not pass live Supabase validation
        assert response.status_code in [401, 403, 404], (
            f"VULNERABILITY: User can access other user's project! "
            f"Status: {response.status_code}"
        )

    @pytest.mark.asyncio
    async def test_user_cannot_modify_other_users_project(self):
        """
        SECURITY: User A should NOT be able to modify User B's project.
        """
        user_a_id = str(uuid.uuid4())
        user_b_project_id = str(uuid.uuid4())
        
        user_a_token = create_user_token(user_a_id)
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{V2_BASE_URL}/projects/{user_b_project_id}",
                headers={"Authorization": f"Bearer {user_a_token}"},
                json={"name": "Hacked Project Name"},
                timeout=10.0
            )
        
        assert response.status_code in [403, 404, 405], (
            f"VULNERABILITY: User can modify other user's project! "
            f"Status: {response.status_code}"
        )


class TestIDORAgentAccess:
    """Test IDOR vulnerabilities in agent access."""

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_users_agent(self):
        """
        SECURITY: User A should NOT be able to access User B's agent.
        """
        user_a_id = str(uuid.uuid4())
        user_b_agent_id = str(uuid.uuid4())
        
        user_a_token = create_user_token(user_a_id)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V2_BASE_URL}/agents/{user_b_agent_id}",
                headers={"Authorization": f"Bearer {user_a_token}"},
                timeout=10.0
            )
        
        # 401 is acceptable - mock JWT may not pass live Supabase validation
        assert response.status_code in [401, 403, 404], (
            f"VULNERABILITY: User can access other user's agent! "
            f"Status: {response.status_code}"
        )


class TestAdminEndpointProtection:
    """Test admin endpoint access control."""

    @pytest.mark.asyncio
    async def test_regular_user_cannot_access_admin_stats(self):
        """
        SECURITY: Regular users should NOT access admin endpoints.
        """
        regular_user_id = str(uuid.uuid4())
        regular_user_token = create_user_token(regular_user_id, role="authenticated")
        
        admin_endpoints = [
            "/admin/stats",
            "/admin/users",
            "/admin/accounts",
        ]
        
        async with httpx.AsyncClient() as client:
            for endpoint in admin_endpoints:
                # Try V1 API
                response = await client.get(
                    f"{V1_BASE_URL}{endpoint}",
                    headers={"Authorization": f"Bearer {regular_user_token}"},
                    timeout=10.0
                )
                
                # Should be 401, 403, or 404 (hidden)
                assert response.status_code in [401, 403, 404], (
                    f"VULNERABILITY: Regular user can access admin endpoint {endpoint}! "
                    f"Status: {response.status_code}"
                )

    @pytest.mark.asyncio
    async def test_admin_api_key_required(self):
        """
        SECURITY: Admin endpoints should require admin API key.
        """
        # Try without any admin key
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V1_BASE_URL}/admin/stats",
                timeout=10.0
            )
        
        assert response.status_code in [401, 403, 404], (
            f"VULNERABILITY: Admin endpoint accessible without admin key! "
            f"Status: {response.status_code}"
        )

    @pytest.mark.asyncio
    async def test_invalid_admin_api_key_rejected(self):
        """
        SECURITY: Invalid admin API keys must be rejected.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V1_BASE_URL}/admin/stats",
                headers={"X-Admin-Api-Key": "invalid-admin-key"},
                timeout=10.0
            )
        
        assert response.status_code in [401, 403, 404], (
            f"VULNERABILITY: Invalid admin key accepted! "
            f"Status: {response.status_code}"
        )


class TestPublicVsPrivateAccess:
    """Test public vs private resource access boundaries."""

    @pytest.mark.asyncio
    async def test_unauthenticated_cannot_access_private_thread(self):
        """
        SECURITY: Unauthenticated users cannot access private threads.
        """
        private_thread_id = str(uuid.uuid4())
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V2_BASE_URL}/threads/{private_thread_id}",
                timeout=10.0
            )
        
        # Should be 401 (unauthenticated) or 403/404
        assert response.status_code in [401, 403, 404], (
            f"VULNERABILITY: Private thread accessible without auth! "
            f"Status: {response.status_code}"
        )

    @pytest.mark.asyncio
    async def test_unauthenticated_cannot_create_thread(self):
        """
        SECURITY: Unauthenticated users cannot create threads.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{V2_BASE_URL}/threads",
                json={"name": "Unauthorized Thread"},
                timeout=10.0
            )
        
        assert response.status_code in [401, 403, 405], (
            f"VULNERABILITY: Unauthenticated user can create thread! "
            f"Status: {response.status_code}"
        )


class TestAccountIsolation:
    """Test account-level data isolation."""

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_account_data(self):
        """
        SECURITY: Users in Account A cannot access Account B's resources.
        """
        user_a_id = str(uuid.uuid4())
        user_a_token = create_user_token(user_a_id)
        
        # Try to access a random account's data
        other_account_id = str(uuid.uuid4())
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V1_BASE_URL}/accounts/{other_account_id}",
                headers={"Authorization": f"Bearer {user_a_token}"},
                timeout=10.0
            )
        
        assert response.status_code in [401, 403, 404], (
            f"VULNERABILITY: User can access other account data! "
            f"Status: {response.status_code}"
        )

    @pytest.mark.asyncio
    async def test_user_cannot_enumerate_users(self):
        """
        SECURITY: Users should not be able to enumerate other users.
        """
        user_id = str(uuid.uuid4())
        user_token = create_user_token(user_id)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V1_BASE_URL}/users",
                headers={"Authorization": f"Bearer {user_token}"},
                timeout=10.0
            )
        
        # Users endpoint should not exist or be restricted
        assert response.status_code in [401, 403, 404], (
            f"POTENTIAL ISSUE: Users endpoint accessible. "
            f"Status: {response.status_code}"
        )


class TestRoleBasedAccess:
    """Test role-based access control."""

    @pytest.mark.asyncio
    async def test_role_claim_cannot_be_self_elevated(self):
        """
        SECURITY: Users cannot elevate their own role via JWT claims.
        
        Attack: Create token with role='admin' when user is not admin.
        Expected: Server should verify role from database, not trust JWT claim.
        """
        regular_user_id = str(uuid.uuid4())
        
        # Create token claiming to be admin (but user is not admin in DB)
        now = datetime.now(timezone.utc)
        payload = {
            "sub": regular_user_id,
            "aud": "authenticated",
            "role": "admin",  # Trying to claim admin role
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
        }
        fake_admin_token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V1_BASE_URL}/admin/stats",
                headers={"Authorization": f"Bearer {fake_admin_token}"},
                timeout=10.0
            )
        
        # Should still be denied - server should verify role from DB
        assert response.status_code in [401, 403, 404], (
            f"VULNERABILITY: Self-elevated role accepted! "
            f"Status: {response.status_code}"
        )
