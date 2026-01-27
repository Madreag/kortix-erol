"""
Database Layer Tests

Tests for database service functions without requiring live database.
Tests serialization, configuration, and error handling.
"""
import pytest
import uuid
from datetime import datetime
from decimal import Decimal


class TestDatabaseSerialization:
    """Test database row serialization utilities."""
    
    def test_serialize_uuid(self):
        """UUID values are serialized to strings."""
        from core.services.db import serialize_row
        
        test_uuid = uuid.uuid4()
        row = {"id": test_uuid, "name": "test"}
        result = serialize_row(row)
        
        assert result["id"] == str(test_uuid)
        assert result["name"] == "test"
    
    def test_serialize_datetime(self):
        """Datetime values are serialized to ISO format."""
        from core.services.db import serialize_row
        
        test_dt = datetime(2026, 1, 27, 12, 0, 0)
        row = {"created_at": test_dt, "name": "test"}
        result = serialize_row(row)
        
        assert result["created_at"] == test_dt.isoformat()
        assert result["name"] == "test"
    
    def test_serialize_decimal(self):
        """Decimal values are serialized to floats."""
        from core.services.db import serialize_row
        
        row = {"amount": Decimal("123.45"), "name": "test"}
        result = serialize_row(row)
        
        assert result["amount"] == 123.45
        assert isinstance(result["amount"], float)
    
    def test_serialize_mixed_row(self):
        """Mixed type rows are serialized correctly."""
        from core.services.db import serialize_row
        
        test_uuid = uuid.uuid4()
        test_dt = datetime(2026, 1, 27, 12, 0, 0)
        
        row = {
            "id": test_uuid,
            "created_at": test_dt,
            "amount": Decimal("99.99"),
            "name": "test",
            "count": 42,
            "active": True,
            "data": None,
        }
        result = serialize_row(row)
        
        assert result["id"] == str(test_uuid)
        assert result["created_at"] == test_dt.isoformat()
        assert result["amount"] == 99.99
        assert result["name"] == "test"
        assert result["count"] == 42
        assert result["active"] is True
        assert result["data"] is None
    
    def test_serialize_rows_list(self):
        """Multiple rows are serialized correctly."""
        from core.services.db import serialize_rows
        
        uuid1 = uuid.uuid4()
        uuid2 = uuid.uuid4()
        
        rows = [
            {"id": uuid1, "name": "test1"},
            {"id": uuid2, "name": "test2"},
        ]
        results = serialize_rows(rows)
        
        assert len(results) == 2
        assert results[0]["id"] == str(uuid1)
        assert results[1]["id"] == str(uuid2)


class TestDatabaseConfiguration:
    """Test database configuration."""
    
    def test_query_type_enum(self):
        """QueryType enum has expected values."""
        from core.services.db import QueryType
        
        assert QueryType.READ.value == "read"
        assert QueryType.WRITE.value == "write"
    
    def test_transient_errors_defined(self):
        """Transient error patterns are defined."""
        from core.services.db import TRANSIENT_ERRORS
        
        assert isinstance(TRANSIENT_ERRORS, tuple)
        assert len(TRANSIENT_ERRORS) > 0
        assert "connection reset" in TRANSIENT_ERRORS
        assert "too many connections" in TRANSIENT_ERRORS
    
    def test_pool_config_exists(self):
        """Pool configuration constants exist."""
        from core.services.db import POOL_SIZE, MAX_OVERFLOW, POOL_TIMEOUT
        
        assert POOL_SIZE > 0
        assert MAX_OVERFLOW >= 0
        assert POOL_TIMEOUT > 0


class TestDatabaseStats:
    """Test database statistics tracking."""
    
    def test_get_db_stats(self):
        """get_db_stats returns expected structure."""
        from core.services.db import get_db_stats
        
        stats = get_db_stats()
        
        assert isinstance(stats, dict)
        assert "primary_reads" in stats
        assert "replica_reads" in stats
        assert "replica_fallbacks" in stats


class TestThreadsRepoSanitization:
    """Test threads repo data sanitization."""
    
    def test_sanitize_null_bytes_string(self):
        """Null bytes are removed from strings."""
        from core.threads.repo import _sanitize_null_bytes
        
        result = _sanitize_null_bytes("hello\u0000world")
        assert result == "helloworld"
    
    def test_sanitize_null_bytes_dict(self):
        """Null bytes are removed from dict values."""
        from core.threads.repo import _sanitize_null_bytes
        
        data = {"name": "test\u0000name", "count": 42}
        result = _sanitize_null_bytes(data)
        
        assert result["name"] == "testname"
        assert result["count"] == 42
    
    def test_sanitize_null_bytes_list(self):
        """Null bytes are removed from list items."""
        from core.threads.repo import _sanitize_null_bytes
        
        data = ["hello\u0000", "world"]
        result = _sanitize_null_bytes(data)
        
        assert result == ["hello", "world"]
    
    def test_sanitize_null_bytes_nested(self):
        """Null bytes are removed from nested structures."""
        from core.threads.repo import _sanitize_null_bytes
        
        data = {
            "items": [{"name": "test\u0000"}],
            "meta": {"key": "value\u0000"}
        }
        result = _sanitize_null_bytes(data)
        
        assert result["items"][0]["name"] == "test"
        assert result["meta"]["key"] == "value"
    
    def test_sanitize_null_bytes_passthrough(self):
        """Non-string types pass through unchanged."""
        from core.threads.repo import _sanitize_null_bytes
        
        assert _sanitize_null_bytes(42) == 42
        assert _sanitize_null_bytes(3.14) == 3.14
        assert _sanitize_null_bytes(True) is True
        assert _sanitize_null_bytes(None) is None


class TestMsgspecDTOs:
    """Test msgspec DTO serialization."""
    
    def test_pagination_dto_structure(self):
        """PaginationDTO has correct structure."""
        from litestar_app.dtos import PaginationDTO
        
        pagination = PaginationDTO(page=1, limit=10, total=100, pages=10)
        
        assert pagination.page == 1
        assert pagination.limit == 10
        assert pagination.total == 100
        assert pagination.pages == 10
    
    def test_thread_dto_defaults(self):
        """ThreadDTO has correct defaults."""
        from litestar_app.dtos import ThreadDTO
        
        thread = ThreadDTO(thread_id="test-123")
        
        assert thread.thread_id == "test-123"
        assert thread.name == "New Chat"
        assert thread.is_public is False
        assert thread.metadata == {}
    
    def test_project_dto_structure(self):
        """ProjectDTO has correct structure."""
        from litestar_app.dtos import ProjectDTO
        
        project = ProjectDTO(
            project_id="proj-123",
            name="Test Project",
            description="A test project"
        )
        
        assert project.project_id == "proj-123"
        assert project.name == "Test Project"
        assert project.is_public is False
    
    def test_agent_dto_defaults(self):
        """AgentDTO has correct defaults."""
        from litestar_app.dtos import AgentDTO
        
        agent = AgentDTO(agent_id="agent-123", name="Test Agent")
        
        assert agent.agent_id == "agent-123"
        assert agent.name == "Test Agent"
        assert agent.is_default is False
        assert agent.version_count == 0
    
    def test_message_response_structure(self):
        """MessageResponse has correct structure."""
        from litestar_app.dtos import MessageResponse
        
        response = MessageResponse(message="Success", thread_id="t-123")
        
        assert response.message == "Success"
        assert response.thread_id == "t-123"
        assert response.project_id is None


class TestMsgspecSerialization:
    """Test msgspec encoding/decoding."""
    
    def test_dto_json_encode(self):
        """DTOs can be encoded to JSON."""
        import msgspec
        from litestar_app.dtos import PaginationDTO
        
        pagination = PaginationDTO(page=1, limit=10, total=100, pages=10)
        encoded = msgspec.json.encode(pagination)
        
        assert isinstance(encoded, bytes)
        assert b'"page":1' in encoded or b'"page": 1' in encoded
    
    def test_dto_json_decode(self):
        """DTOs can be decoded from JSON."""
        import msgspec
        from litestar_app.dtos import PaginationDTO
        
        json_data = b'{"page":2,"limit":20,"total":50,"pages":3}'
        pagination = msgspec.json.decode(json_data, type=PaginationDTO)
        
        assert pagination.page == 2
        assert pagination.limit == 20
        assert pagination.total == 50
        assert pagination.pages == 3
    
    def test_thread_list_response_encode(self):
        """ThreadListResponse can be encoded."""
        import msgspec
        from litestar_app.dtos import ThreadDTO, ThreadListResponse, PaginationDTO
        
        threads = [ThreadDTO(thread_id="t-1"), ThreadDTO(thread_id="t-2")]
        pagination = PaginationDTO(page=1, limit=10, total=2, pages=1)
        response = ThreadListResponse(threads=threads, pagination=pagination)
        
        encoded = msgspec.json.encode(response)
        assert isinstance(encoded, bytes)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
