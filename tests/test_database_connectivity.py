"""
Unit tests for database connectivity enhancements.

Tests connection pooling, custom SQL queries, driver detection, and error handling.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from core.db.connection_pool import DatabaseConnectionPool, get_connection_pool
from core.db.drivers import (
    detect_db_type,
    check_driver_installed,
    get_installation_command,
    validate_driver_or_raise
)
from core.db.exceptions import (
    DatabaseConnectionError,
    DatabaseDriverError,
    DatabaseQueryError
)
from core.audit.loader import load_table


class TestConnectionPool:
    """Test database connection pooling functionality."""
    
    def setup_method(self):
        """Reset singleton before each test."""
        if DatabaseConnectionPool._instance:
            DatabaseConnectionPool._instance.close_all()
            DatabaseConnectionPool._instance = None
    
    def teardown_method(self):
        """Clean up after test."""
        if DatabaseConnectionPool._instance:
            DatabaseConnectionPool._instance.close_all()
            DatabaseConnectionPool._instance = None
    
    def test_singleton_pattern(self):
        """Test that connection pool uses singleton pattern."""
        pool1 = DatabaseConnectionPool()
        pool2 = DatabaseConnectionPool()
        assert pool1 is pool2, "Connection pool should be a singleton"
    
    def test_get_connection_pool_function(self):
        """Test get_connection_pool helper function."""
        pool1 = get_connection_pool()
        pool2 = get_connection_pool()
        assert pool1 is pool2, "get_connection_pool should return same instance"
    
    @patch('core.db.connection_pool.event')
    @patch('core.db.connection_pool.create_engine')
    def test_engine_creation(self, mock_create_engine, mock_event):
        """Test that engine is created with correct parameters."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        
        pool = DatabaseConnectionPool()
        engine = pool.get_engine("postgresql://user:pass@localhost/db")
        
        assert mock_create_engine.called
        assert engine == mock_engine
    
    @patch('core.db.connection_pool.event')
    @patch('core.db.connection_pool.create_engine')
    def test_engine_reuse(self, mock_create_engine, mock_event):
        """Test that same connection string reuses engine."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        
        pool = DatabaseConnectionPool()
        engine1 = pool.get_engine("postgresql://user:pass@localhost/db")
        engine2 = pool.get_engine("postgresql://user:pass@localhost/db")
        
        assert engine1 is engine2
        assert mock_create_engine.call_count == 1, "Engine should be created only once"
    
    @patch('core.db.connection_pool.event')
    @patch('core.db.connection_pool.create_engine')
    def test_different_connections(self, mock_create_engine, mock_event):
        """Test that different connection strings create different engines."""
        mock_engine1 = Mock()
        mock_engine2 = Mock()
        mock_create_engine.side_effect = [mock_engine1, mock_engine2]
        
        pool = DatabaseConnectionPool()
        engine1 = pool.get_engine("postgresql://user:pass@localhost/db1")
        engine2 = pool.get_engine("postgresql://user:pass@localhost/db2")
        
        assert engine1 is not engine2
        assert mock_create_engine.call_count == 2
    
    def test_sanitize_uri(self):
        """Test that passwords are sanitized in URIs."""
        pool = DatabaseConnectionPool()
        
        uri = "postgresql://user:secretpass@localhost:5432/db"
        sanitized = pool._sanitize_uri(uri)
        
        assert "secretpass" not in sanitized
        assert "***" in sanitized
        assert "user" in sanitized
        assert "localhost" in sanitized


class TestDriverDetection:
    """Test database driver detection and validation."""
    
    def test_detect_postgresql(self):
        """Test PostgreSQL detection."""
        assert detect_db_type("postgresql://localhost/db") == "postgresql"
        assert detect_db_type("postgres://localhost/db") == "postgresql"
    
    def test_detect_mysql(self):
        """Test MySQL detection."""
        assert detect_db_type("mysql://localhost/db") == "mysql"
        assert detect_db_type("mysql+pymysql://localhost/db") == "mysql"
    
    def test_detect_mssql(self):
        """Test SQL Server detection."""
        assert detect_db_type("mssql://localhost/db") == "mssql"
        assert detect_db_type("sqlserver://localhost/db") == "mssql"
    
    def test_detect_oracle(self):
        """Test Oracle detection."""
        assert detect_db_type("oracle://localhost/db") == "oracle"
    
    def test_detect_sqlite(self):
        """Test SQLite detection."""
        assert detect_db_type("sqlite:///path/to/db.sqlite") == "sqlite"
    
    def test_detect_unknown(self):
        """Test unknown database type."""
        assert detect_db_type("unknown://localhost/db") is None
    
    def test_check_sqlite_installed(self):
        """Test that sqlite3 is always installed (built-in)."""
        assert check_driver_installed("sqlite") is True
    
    def test_get_installation_command(self):
        """Test getting installation commands."""
        cmd = get_installation_command("postgresql")
        assert "psycopg2" in cmd
        assert "pip install" in cmd


class TestDatabaseExceptions:
    """Test database exception formatting."""
    
    def test_connection_error_authentication(self):
        """Test authentication error formatting."""
        original_error = Exception("authentication failed for user")
        error = DatabaseConnectionError(
            uri="postgresql://user:secret123@localhost/db",
            original_error=original_error
        )
        
        error_msg = str(error)
        assert "Authentication failed" in error_msg
        assert "Check username and password" in error_msg
        assert "secret123" not in error_msg  # Password should be sanitized
    
    def test_connection_error_network(self):
        """Test network connection error formatting."""
        original_error = Exception("could not connect to server")
        error = DatabaseConnectionError(
            uri="postgresql://user:pass@localhost/db",
            original_error=original_error
        )
        
        error_msg = str(error)
        assert "Could not connect" in error_msg
        assert "Check if database server is running" in error_msg
    
    def test_connection_error_table_not_found(self):
        """Test table not found error formatting."""
        original_error = Exception("no such table: users")
        error = DatabaseConnectionError(
            uri="sqlite:///test.db",
            original_error=original_error,
            table_name="users"
        )
        
        error_msg = str(error)
        assert "Table not found" in error_msg
        assert "users" in error_msg
    
    def test_driver_error(self):
        """Test driver error formatting."""
        error = DatabaseDriverError(
            db_type="postgresql",
            driver_name="psycopg2",
            install_command="pip install psycopg2-binary"
        )
        
        error_msg = str(error)
        assert "psycopg2" in error_msg
        assert "pip install" in error_msg
    
    def test_query_error(self):
        """Test SQL query error formatting."""
        original_error = Exception("syntax error near SELECT")
        error = DatabaseQueryError(
            query="SELECT * FROM users WHERE",
            uri="postgresql://localhost/db",
            original_error=original_error
        )
        
        error_msg = str(error)
        assert "SQL query failed" in error_msg
        assert "SELECT * FROM users WHERE" in error_msg
        assert "syntax error" in error_msg


class TestCustomQueries:
    """Test custom SQL query functionality."""
    
    @patch('core.audit.loader.get_connection_pool')
    @patch('core.audit.loader.validate_driver_or_raise')
    @patch('pandas.read_sql_query')
    def test_load_table_with_custom_query(self, mock_read_sql, mock_validate, mock_pool):
        """Test loading table with custom SQL query."""
        # Setup mocks
        mock_validate.return_value = ("postgresql", True)
        mock_engine = Mock()
        mock_pool_instance = Mock()
        mock_pool_instance.get_engine.return_value = mock_engine
        mock_pool.return_value = mock_pool_instance
        
        mock_df = pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]})
        mock_read_sql.return_value = mock_df
        
        # Test
        query = "SELECT * FROM users WHERE active = true"
        result = load_table(
            path="postgresql://user:pass@localhost/db/users",
            query=query
        )
        
        # Verify
        assert mock_read_sql.called
        call_args = mock_read_sql.call_args
        assert call_args[0][0] == query  # First arg should be the query
        assert result.equals(mock_df)
    
    @patch('core.audit.loader.get_connection_pool')
    @patch('core.audit.loader.validate_driver_or_raise')
    @patch('pandas.read_sql_table')
    def test_load_table_without_custom_query(self, mock_read_sql, mock_validate, mock_pool):
        """Test loading table without custom query (default behavior)."""
        # Setup mocks
        mock_validate.return_value = ("postgresql", True)
        mock_engine = Mock()
        mock_pool_instance = Mock()
        mock_pool_instance.get_engine.return_value = mock_engine
        mock_pool.return_value = mock_pool_instance
        
        mock_df = pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]})
        mock_read_sql.return_value = mock_df
        
        # Test
        result = load_table(path="postgresql://user:pass@localhost/db/users")
        
        # Verify
        assert mock_read_sql.called
        call_args = mock_read_sql.call_args
        assert call_args[0][0] == "users"  # First arg should be table name
        assert result.equals(mock_df)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
