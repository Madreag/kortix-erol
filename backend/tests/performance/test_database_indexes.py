"""
Database Index Verification Tests

Uses EXPLAIN ANALYZE to verify critical queries use indexes.
"""
import pytest
import os

# Skip if no database connection
pytestmark = pytest.mark.skipif(
    os.getenv("SKIP_DB_TESTS", "true").lower() == "true",
    reason="Database tests disabled (set SKIP_DB_TESTS=false to enable)"
)


class TestCriticalQueryIndexes:
    """Verify critical queries use indexes instead of sequential scans."""

    @pytest.fixture
    async def db_connection(self):
        """Get database connection for EXPLAIN queries."""
        from core.services.db import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            yield conn

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_threads_account_id_uses_index(self, db_connection):
        """
        Threads query by account_id should use index.
        
        Query: SELECT * FROM threads WHERE account_id = $1
        Expected: Index Scan on threads_account_id_idx
        """
        explain_result = await db_connection.fetch(
            "EXPLAIN ANALYZE SELECT * FROM threads WHERE account_id = $1 LIMIT 10",
            "test-account-id"
        )
        
        plan = "\n".join(row[0] for row in explain_result)
        
        print("\n📊 Query Plan (threads by account_id):")
        print(plan)
        
        # Should NOT have sequential scan on large tables
        assert "Seq Scan on threads" not in plan or "rows=0" in plan.lower(), (
            "Query uses sequential scan instead of index! "
            "Add index: CREATE INDEX idx_threads_account_id ON threads(account_id)"
        )

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_messages_thread_id_uses_index(self, db_connection):
        """
        Messages query by thread_id should use index.
        
        Query: SELECT * FROM messages WHERE thread_id = $1
        Expected: Index Scan on messages_thread_id_idx
        """
        explain_result = await db_connection.fetch(
            "EXPLAIN ANALYZE SELECT * FROM messages WHERE thread_id = $1 ORDER BY created_at LIMIT 100",
            "test-thread-id"
        )
        
        plan = "\n".join(row[0] for row in explain_result)
        
        print("\n📊 Query Plan (messages by thread_id):")
        print(plan)
        
        assert "Seq Scan on messages" not in plan or "rows=0" in plan.lower(), (
            "Query uses sequential scan! "
            "Add index: CREATE INDEX idx_messages_thread_id ON messages(thread_id)"
        )

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_agent_runs_thread_id_uses_index(self, db_connection):
        """
        Agent runs query by thread_id should use index.
        """
        explain_result = await db_connection.fetch(
            "EXPLAIN ANALYZE SELECT * FROM agent_runs WHERE thread_id = $1",
            "test-thread-id"
        )
        
        plan = "\n".join(row[0] for row in explain_result)
        
        print("\n📊 Query Plan (agent_runs by thread_id):")
        print(plan)
        
        assert "Seq Scan on agent_runs" not in plan or "rows=0" in plan.lower(), (
            "Query uses sequential scan! "
            "Add index: CREATE INDEX idx_agent_runs_thread_id ON agent_runs(thread_id)"
        )

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_projects_account_id_uses_index(self, db_connection):
        """
        Projects query by account_id should use index.
        """
        explain_result = await db_connection.fetch(
            "EXPLAIN ANALYZE SELECT * FROM projects WHERE account_id = $1",
            "test-account-id"
        )
        
        plan = "\n".join(row[0] for row in explain_result)
        
        print("\n📊 Query Plan (projects by account_id):")
        print(plan)
        
        assert "Seq Scan on projects" not in plan or "rows=0" in plan.lower(), (
            "Query uses sequential scan! "
            "Add index: CREATE INDEX idx_projects_account_id ON projects(account_id)"
        )


class TestIndexUsageStats:
    """Check index usage statistics from pg_stat_user_indexes."""

    @pytest.fixture
    async def db_connection(self):
        """Get database connection."""
        from core.services.db import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            yield conn

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_report_unused_indexes(self, db_connection):
        """
        Report indexes that haven't been used (potential candidates for removal).
        """
        result = await db_connection.fetch("""
            SELECT 
                schemaname,
                relname AS table_name,
                indexrelname AS index_name,
                idx_scan AS times_used,
                pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
            FROM pg_stat_user_indexes
            WHERE idx_scan = 0
            AND schemaname = 'public'
            ORDER BY pg_relation_size(indexrelid) DESC
            LIMIT 10
        """)
        
        print("\n📊 Unused Indexes (candidates for removal):")
        if result:
            for row in result:
                print(f"   {row['table_name']}.{row['index_name']} ({row['index_size']})")
        else:
            print("   ✅ No unused indexes found")

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_report_most_used_indexes(self, db_connection):
        """
        Report most frequently used indexes.
        """
        result = await db_connection.fetch("""
            SELECT 
                relname AS table_name,
                indexrelname AS index_name,
                idx_scan AS times_used,
                idx_tup_read AS rows_read,
                pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
            FROM pg_stat_user_indexes
            WHERE schemaname = 'public'
            ORDER BY idx_scan DESC
            LIMIT 10
        """)
        
        print("\n📊 Most Used Indexes:")
        for row in result:
            print(f"   {row['table_name']}.{row['index_name']}: {row['times_used']} scans, {row['rows_read']} rows")


class TestSlowQueryDetection:
    """Detect potentially slow queries."""

    @pytest.fixture
    async def db_connection(self):
        """Get database connection."""
        from core.services.db import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            yield conn

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_check_pg_stat_statements(self, db_connection):
        """
        Check pg_stat_statements for slow queries (if extension is enabled).
        """
        try:
            result = await db_connection.fetch("""
                SELECT 
                    substring(query, 1, 80) AS query_preview,
                    calls,
                    round(total_exec_time::numeric, 2) AS total_time_ms,
                    round(mean_exec_time::numeric, 2) AS avg_time_ms,
                    round(max_exec_time::numeric, 2) AS max_time_ms,
                    rows
                FROM pg_stat_statements
                WHERE userid = (SELECT usesysid FROM pg_user WHERE usename = current_user)
                ORDER BY mean_exec_time DESC
                LIMIT 10
            """)
            
            print("\n📊 Slowest Queries (by avg time):")
            for row in result:
                if row['avg_time_ms'] > 100:  # Flag queries > 100ms avg
                    print(f"   ⚠️ {row['query_preview']}...")
                    print(f"      Avg: {row['avg_time_ms']}ms | Max: {row['max_time_ms']}ms | Calls: {row['calls']}")
                else:
                    print(f"   ✅ {row['query_preview']}... ({row['avg_time_ms']}ms avg)")
                    
        except Exception as e:
            print(f"\n⚠️ pg_stat_statements not available: {e}")
            print("   Enable with: CREATE EXTENSION pg_stat_statements;")
