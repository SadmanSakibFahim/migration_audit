"""
Database-specific exceptions with helpful error messages.

Provides clear, actionable error messages for common database connectivity issues.
"""

from typing import Optional


class DatabaseConnectionError(Exception):
    """
    Raised when database connection fails.
    
    Provides helpful guidance based on the type of connection error.
    """
    
    def __init__(self, uri: str, original_error: Exception, table_name: Optional[str] = None):
        self.uri = uri
        self.original_error = original_error
        self.table_name = table_name
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """Format error message with helpful guidance."""
        error_str = str(self.original_error).lower()
        safe_uri = self._sanitize_uri(self.uri)
        
        # Provide helpful guidance based on error type
        if "authentication failed" in error_str or "access denied" in error_str:
            return (
                f"❌ Authentication failed for {safe_uri}\n"
                f"   → Check username and password\n"
                f"   → Verify user has necessary permissions\n"
                f"   Original error: {self.original_error}"
            )
        
        elif "could not connect" in error_str or "connection refused" in error_str:
            return (
                f"❌ Could not connect to {safe_uri}\n"
                f"   → Check if database server is running\n"
                f"   → Verify host and port are correct\n"
                f"   → Check firewall settings\n"
                f"   Original error: {self.original_error}"
            )
        
        elif "timeout" in error_str:
            return (
                f"❌ Connection timeout for {safe_uri}\n"
                f"   → Database server may be overloaded\n"
                f"   → Network latency may be high\n"
                f"   → Try increasing timeout value\n"
                f"   Original error: {self.original_error}"
            )
        
        elif "database" in error_str and "does not exist" in error_str:
            return (
                f"❌ Database does not exist: {safe_uri}\n"
                f"   → Verify database name is correct\n"
                f"   → Check if database has been created\n"
                f"   Original error: {self.original_error}"
            )
        
        elif "no such table" in error_str or "table" in error_str and "not found" in error_str:
            table_info = f" (table: {self.table_name})" if self.table_name else ""
            return (
                f"❌ Table not found in {safe_uri}{table_info}\n"
                f"   → Verify table name is correct\n"
                f"   → Check table exists in the database\n"
                f"   → Verify schema/database name\n"
                f"   Original error: {self.original_error}"
            )
        
        elif "ssl" in error_str or "tls" in error_str:
            return (
                f"❌ SSL/TLS connection error for {safe_uri}\n"
                f"   → Check SSL certificate configuration\n"
                f"   → Try adding '?sslmode=require' or '?sslmode=disable' to URI\n"
                f"   Original error: {self.original_error}"
            )
        
        else:
            return (
                f"❌ Database error for {safe_uri}\n"
                f"   Original error: {self.original_error}"
            )
    
    @staticmethod
    def _sanitize_uri(uri: str) -> str:
        """Remove password from URI for safe error messages."""
        import re
        pattern = r'(://[^:]+:)([^@]+)(@)'
        return re.sub(pattern, r'\1***\3', uri)


class DatabaseDriverError(Exception):
    """
    Raised when required database driver is not installed.
    
    Provides installation instructions for the missing driver.
    """
    
    def __init__(self, db_type: str, driver_name: str, install_command: str):
        self.db_type = db_type
        self.driver_name = driver_name
        self.install_command = install_command
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """Format error message with installation instructions."""
        return (
            f"❌ Database driver '{self.driver_name}' not installed for {self.db_type}\n"
            f"   → Install with: {self.install_command}\n"
            f"   → Then restart the audit"
        )


class DatabaseQueryError(Exception):
    """
    Raised when a custom SQL query fails.
    
    Provides context about the failed query.
    """
    
    def __init__(self, query: str, uri: str, original_error: Exception):
        self.query = query
        self.uri = uri
        self.original_error = original_error
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """Format error message with query context."""
        safe_uri = DatabaseConnectionError._sanitize_uri(self.uri)
        # Truncate long queries
        query_preview = self.query[:200] + "..." if len(self.query) > 200 else self.query
        
        return (
            f"❌ SQL query failed on {safe_uri}\n"
            f"   Query: {query_preview}\n"
            f"   Error: {self.original_error}\n"
            f"   → Check SQL syntax\n"
            f"   → Verify column and table names\n"
            f"   → Check user permissions"
        )


class DatabaseConfigurationError(Exception):
    """
    Raised when database configuration is invalid.
    """
    
    def __init__(self, message: str):
        super().__init__(f"❌ Database configuration error: {message}")
