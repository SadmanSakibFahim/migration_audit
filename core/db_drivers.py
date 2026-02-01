"""
Database driver detection and installation guidance.

Automatically detects missing database drivers and provides installation instructions.
"""

from typing import Dict, Optional, Tuple
from core.logger import get_logger
from core.db_exceptions import DatabaseDriverError

logger = get_logger(__name__)


# Database driver information
DB_DRIVERS = {
    "postgresql": {
        "driver": "psycopg2",
        "install": "pip install psycopg2-binary",
        "test_import": "psycopg2",
        "description": "PostgreSQL adapter"
    },
    "mysql": {
        "driver": "pymysql",
        "install": "pip install pymysql",
        "test_import": "pymysql",
        "description": "MySQL/MariaDB connector"
    },
    "mssql": {
        "driver": "pyodbc",
        "install": "pip install pyodbc",
        "test_import": "pyodbc",
        "description": "Microsoft SQL Server driver"
    },
    "oracle": {
        "driver": "cx_Oracle",
        "install": "pip install cx_Oracle",
        "test_import": "cx_Oracle",
        "description": "Oracle database driver"
    },
    "sqlite": {
        "driver": "sqlite3",
        "install": "Built-in (no installation needed)",
        "test_import": "sqlite3",
        "description": "SQLite (built-in)"
    }
}


def detect_db_type(uri: str) -> Optional[str]:
    """
    Detect database type from connection URI.
    
    Args:
        uri: Database connection URI
    
    Returns:
        Database type (e.g., 'postgresql', 'mysql') or None if unknown
    
    Examples:
        >>> detect_db_type("postgresql://user:pass@localhost/db")
        'postgresql'
        >>> detect_db_type("mysql+pymysql://user:pass@localhost/db")
        'mysql'
    """
    uri_lower = uri.lower()
    
    if uri_lower.startswith("postgresql://") or uri_lower.startswith("postgres://"):
        return "postgresql"
    elif uri_lower.startswith("mysql://") or "mysql" in uri_lower:
        return "mysql"
    elif uri_lower.startswith("mssql://") or uri_lower.startswith("sqlserver://"):
        return "mssql"
    elif uri_lower.startswith("oracle://"):
        return "oracle"
    elif uri_lower.startswith("sqlite://"):
        return "sqlite"
    
    return None


def check_driver_installed(db_type: str) -> bool:
    """
    Check if required driver is installed for the database type.
    
    Args:
        db_type: Database type (e.g., 'postgresql', 'mysql')
    
    Returns:
        True if driver is installed, False otherwise
    """
    if db_type not in DB_DRIVERS:
        logger.warning(f"Unknown database type: {db_type}")
        return True  # Assume it's fine if we don't know about it
    
    driver_info = DB_DRIVERS[db_type]
    try:
        __import__(driver_info["test_import"])
        logger.debug(f"Driver '{driver_info['driver']}' for {db_type} is installed")
        return True
    except ImportError:
        logger.warning(f"Driver '{driver_info['driver']}' for {db_type} is NOT installed")
        return False


def get_installation_command(db_type: str) -> str:
    """
    Get pip install command for database driver.
    
    Args:
        db_type: Database type (e.g., 'postgresql', 'mysql')
    
    Returns:
        Installation command string
    """
    return DB_DRIVERS.get(db_type, {}).get("install", "Unknown driver")


def get_driver_info(db_type: str) -> Optional[Dict[str, str]]:
    """
    Get complete driver information for a database type.
    
    Args:
        db_type: Database type (e.g., 'postgresql', 'mysql')
    
    Returns:
        Dictionary with driver information or None if unknown
    """
    return DB_DRIVERS.get(db_type)


def validate_driver_or_raise(uri: str) -> Tuple[str, bool]:
    """
    Validate that required driver is installed, raise exception if not.
    
    Args:
        uri: Database connection URI
    
    Returns:
        Tuple of (db_type, is_installed)
    
    Raises:
        DatabaseDriverError: If required driver is not installed
    """
    db_type = detect_db_type(uri)
    
    if db_type is None:
        logger.warning(f"Could not detect database type from URI: {uri[:50]}...")
        return ("unknown", True)
    
    is_installed = check_driver_installed(db_type)
    
    if not is_installed:
        driver_info = DB_DRIVERS[db_type]
        raise DatabaseDriverError(
            db_type=db_type,
            driver_name=driver_info["driver"],
            install_command=driver_info["install"]
        )
    
    return (db_type, is_installed)


def list_all_drivers() -> Dict[str, Dict[str, str]]:
    """
    Get information about all supported database drivers.
    
    Returns:
        Dictionary mapping database types to driver information
    """
    return DB_DRIVERS.copy()


def check_all_drivers() -> Dict[str, bool]:
    """
    Check installation status of all known drivers.
    
    Returns:
        Dictionary mapping database types to installation status
    """
    status = {}
    for db_type in DB_DRIVERS.keys():
        status[db_type] = check_driver_installed(db_type)
    return status


def print_driver_status():
    """Print installation status of all database drivers."""
    print("\n" + "=" * 60)
    print("DATABASE DRIVER STATUS")
    print("=" * 60)
    
    status = check_all_drivers()
    
    for db_type, is_installed in status.items():
        driver_info = DB_DRIVERS[db_type]
        status_icon = "✅" if is_installed else "❌"
        status_text = "INSTALLED" if is_installed else "NOT INSTALLED"
        
        print(f"\n{status_icon} {db_type.upper()}: {status_text}")
        print(f"   Driver: {driver_info['driver']}")
        print(f"   Description: {driver_info['description']}")
        
        if not is_installed:
            print(f"   Install: {driver_info['install']}")
    
    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    # When run directly, print driver status
    print_driver_status()
