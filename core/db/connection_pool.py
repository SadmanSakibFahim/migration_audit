"""
Database Connection Pool Manager

Provides singleton connection pool for efficient database connection reuse
across multiple table loads during audit execution.
"""

from sqlalchemy import create_engine, pool, event
from sqlalchemy.engine import Engine
from typing import Dict, Optional
from contextlib import contextmanager
import threading
from core.audit.logger import get_logger

logger = get_logger(__name__)


class DatabaseConnectionPool:
    """
    Singleton connection pool manager for database connections.
    Reuses connections across multiple table loads to improve performance.
    
    Features:
    - Connection pooling with configurable pool size
    - Pre-ping to verify connection health
    - Automatic connection recycling
    - Thread-safe singleton pattern
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._pools = {}
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the connection pool manager."""
        if not self._initialized:
            self._pools: Dict[str, Engine] = {}
            self._initialized = True
            logger.info("DatabaseConnectionPool initialized")
    
    def get_engine(
        self,
        connection_string: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 3600
    ) -> Engine:
        """
        Get or create a pooled engine for the connection string.
        
        Args:
            connection_string: Database connection URI
            pool_size: Number of connections to maintain in the pool
            max_overflow: Maximum number of connections to create beyond pool_size
            pool_timeout: Seconds to wait for a connection from the pool
            pool_recycle: Seconds after which to recycle connections
        
        Returns:
            SQLAlchemy Engine with connection pooling
        """
        # Sanitize connection string for logging (remove password)
        safe_uri = self._sanitize_uri(connection_string)
        
        if connection_string not in self._pools:
            logger.info(f"Creating new connection pool for: {safe_uri}")
            
            try:
                engine = create_engine(
                    connection_string,
                    poolclass=pool.QueuePool,
                    pool_size=pool_size,
                    max_overflow=max_overflow,
                    pool_timeout=pool_timeout,
                    pool_pre_ping=True,  # Verify connections before use
                    pool_recycle=pool_recycle,  # Recycle connections after N seconds
                    echo=False,  # Set to True for SQL query logging
                )
                
                # Add event listener for connection checkout (for debugging)
                @event.listens_for(engine, "connect")
                def receive_connect(dbapi_conn, connection_record):
                    logger.debug(f"Database connection established: {safe_uri}")
                
                self._pools[connection_string] = engine
                logger.info(
                    f"Connection pool created: {safe_uri} "
                    f"(pool_size={pool_size}, max_overflow={max_overflow})"
                )
            except Exception as e:
                logger.error(f"Failed to create connection pool for {safe_uri}: {e}")
                raise
        else:
            logger.debug(f"Reusing existing connection pool: {safe_uri}")
        
        return self._pools[connection_string]
    
    def close_all(self):
        """Close all connection pools and release resources."""
        logger.info(f"Closing {len(self._pools)} connection pool(s)")
        for uri, engine in self._pools.items():
            safe_uri = self._sanitize_uri(uri)
            try:
                engine.dispose()
                logger.info(f"Connection pool closed: {safe_uri}")
            except Exception as e:
                logger.error(f"Error closing connection pool {safe_uri}: {e}")
        
        self._pools.clear()
        logger.info("All connection pools closed")
    
    def get_pool_status(self, connection_string: str) -> Optional[Dict]:
        """
        Get status information about a connection pool.
        
        Args:
            connection_string: Database connection URI
        
        Returns:
            Dictionary with pool status or None if pool doesn't exist
        """
        if connection_string not in self._pools:
            return None
        
        engine = self._pools[connection_string]
        pool_obj = engine.pool
        
        return {
            "size": pool_obj.size(),
            "checked_in": pool_obj.checkedin(),
            "checked_out": pool_obj.checkedout(),
            "overflow": pool_obj.overflow(),
            "status": pool_obj.status()
        }
    
    @staticmethod
    def _sanitize_uri(uri: str) -> str:
        """
        Remove password from URI for safe logging.
        
        Args:
            uri: Database connection URI
        
        Returns:
            Sanitized URI with password replaced by '***'
        """
        import re
        # Pattern: dialect://user:password@host:port/db
        pattern = r'(://[^:]+:)([^@]+)(@)'
        return re.sub(pattern, r'\1***\3', uri)
    
    def __del__(self):
        """Cleanup on garbage collection."""
        if hasattr(self, '_pools') and self._pools:
            self.close_all()


# Singleton instance
_pool_instance = None


def get_connection_pool() -> DatabaseConnectionPool:
    """
    Get the singleton connection pool instance.
    
    Returns:
        DatabaseConnectionPool singleton instance
    """
    global _pool_instance
    if _pool_instance is None:
        _pool_instance = DatabaseConnectionPool()
    return _pool_instance
