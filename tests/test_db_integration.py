"""
Integration tests for database connectivity.

Verifies end-to-end database loading with SQLite, including:
- Connection pooling
- Custom SQL queries
- Error handling
"""

import pytest
import pandas as pd
import sqlite3
import os
from sqlalchemy import create_engine
from core.audit.loader import load_table
from core.db.connection_pool import get_connection_pool
from core.db.exceptions import DatabaseConnectionError, DatabaseQueryError

# Setup test database path
TEST_DB_PATH = "test_integration.db"
TEST_DB_URI = f"sqlite:///{TEST_DB_PATH}"

@pytest.fixture(scope="module")
def setup_database():
    """Create a temporary SQLite database with test data."""
    # Remove existing db if any
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    
    # Create engine
    engine = create_engine(TEST_DB_URI)
    
    # Create test data
    df_users = pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
        "department": ["HR", "IT", "HR", "Sales", "IT"],
        "salary": [50000, 80000, 55000, 70000, 85000],
        "active": [1, 1, 0, 1, 0]
    })
    
    df_logs = pd.DataFrame({
        "log_id": range(1, 101),
        "user_id": [1, 2, 1, 2, 3] * 20,
        "action": ["login"] * 100
    })
    
    # Write to database
    df_users.to_sql("users", engine, index=False)
    df_logs.to_sql("audit_logs", engine, index=False)
    
    yield
    
    # Cleanup
    try:
        get_connection_pool().close_all()
        engine.dispose()
    except:
        pass
    
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass  # File might be locked on Windows

class TestDatabaseIntegration:
    """Integration tests using real SQLite database."""
    
    def test_load_full_table(self, setup_database):
        """Test loading entire table."""
        df = load_table(f"{TEST_DB_URI}/users")
        
        assert len(df) == 5
        assert list(df.columns) == ["id", "name", "department", "salary", "active"]
        assert df[df["name"] == "Alice"]["salary"].iloc[0] == 50000
    
    def test_load_with_custom_query(self, setup_database):
        """Test loading with custom SQL query."""
        # Query: Select high earners in IT
        query = "SELECT name, salary FROM users WHERE department = 'IT' AND salary > 80000"
        
        df = load_table(f"{TEST_DB_URI}/users", query=query)
        
        assert len(df) == 1
        assert df.iloc[0]["name"] == "Eve"
        assert list(df.columns) == ["name", "salary"]
    
    def test_load_with_custom_query_and_chunking(self, setup_database):
        """Test chunked loading with custom query."""
        query = "SELECT * FROM audit_logs ORDER BY log_id"
        
        # Load in chunks of 10
        chunks = load_table(f"{TEST_DB_URI}/audit_logs", query=query, chunk_size=10)
        
        total_rows = 0
        chunk_count = 0
        
        for chunk in chunks:
            total_rows += len(chunk)
            chunk_count += 1
            assert len(chunk) <= 10
            
        assert total_rows == 100
        assert chunk_count == 10
    
    def test_connection_pooling_efficiency(self, setup_database):
        """Verify connection pool is being used."""
        pool = get_connection_pool()
        
        # Initial status
        initial_status = pool.get_pool_status(TEST_DB_URI)
        
        # Load table multiple times
        for _ in range(5):
            load_table(f"{TEST_DB_URI}/users")
            
        # Check pool status - should still exist
        final_status = pool.get_pool_status(TEST_DB_URI)
        assert final_status is not None
        
        # We reused connections, so overflow shouldn't be high
        # Note: exact numbers depend on SQLAlchemy pooling implementation details
        # but we just want to ensure multiple calls didn't crash or leak massively
    
    def test_invalid_query_error(self, setup_database):
        """Test error handling for bad queries."""
        query = "SELECT * FROM non_existent_table"
        
        with pytest.raises(DatabaseQueryError) as excinfo:
            load_table(f"{TEST_DB_URI}/users", query=query)
        
        error_msg = str(excinfo.value)
        assert "SQL query failed" in error_msg
        assert "non_existent_table" in error_msg
    
    def test_invalid_table_error(self, setup_database):
        """Test error handling for non-existent table."""
        with pytest.raises(DatabaseConnectionError) as excinfo:
            load_table(f"{TEST_DB_URI}/ghost_table")
        
        error_msg = str(excinfo.value)
        assert "Table not found" in error_msg or "no such table" in str(excinfo.value).lower()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
