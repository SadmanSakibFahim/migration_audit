import pytest
from unittest.mock import patch

from core.db.drivers import (
    detect_db_type,
    check_driver_installed,
    get_installation_command,
    get_driver_info,
    validate_driver_or_raise,
    list_all_drivers,
    check_all_drivers,
    print_driver_status
)
from core.db.exceptions import DatabaseDriverError

def test_detect_db_type():
    assert detect_db_type("postgresql://user:pass@localhost/db") == "postgresql"
    assert detect_db_type("postgres://user:pass@localhost/db") == "postgresql"
    assert detect_db_type("mysql+pymysql://user:pass@localhost/db") == "mysql"
    assert detect_db_type("mssql://user:pass@localhost/db") == "mssql"
    assert detect_db_type("sqlserver://user:pass@localhost/db") == "mssql"
    assert detect_db_type("oracle://user:pass@localhost/db") == "oracle"
    assert detect_db_type("sqlite:///data.db") == "sqlite"
    assert detect_db_type("unknown://user:pass@localhost/db") is None

def test_check_driver_installed_unknown():
    # Unknown driver should return True to prevent blocking unknown/custom drivers
    assert check_driver_installed("unknown_db") is True

@patch("builtins.__import__")
def test_check_driver_installed_success(mock_import):
    mock_import.return_value = True
    assert check_driver_installed("postgresql") is True

@patch("builtins.__import__", side_effect=ImportError("No module"))
def test_check_driver_installed_failure(mock_import):
    assert check_driver_installed("postgresql") is False

def test_get_installation_command():
    assert "pip install psycopg2-binary" in get_installation_command("postgresql")
    assert get_installation_command("unknown") == "Unknown driver"

def test_get_driver_info():
    info = get_driver_info("postgresql")
    assert info is not None
    assert info["driver"] == "psycopg2"
    assert get_driver_info("unknown") is None

@patch("core.db.drivers.check_driver_installed", return_value=True)
def test_validate_driver_or_raise_success(mock_check):
    db_type, installed = validate_driver_or_raise("postgresql://user:pass@localhost/db")
    assert db_type == "postgresql"
    assert installed is True

@patch("core.db.drivers.check_driver_installed", return_value=False)
def test_validate_driver_or_raise_failure(mock_check):
    with pytest.raises(DatabaseDriverError) as exc_info:
        validate_driver_or_raise("postgresql://user:pass@localhost/db")
    assert "psycopg2" in str(exc_info.value)
    
def test_validate_driver_or_raise_unknown_uri():
    db_type, installed = validate_driver_or_raise("unknown://test")
    assert db_type == "unknown"
    assert installed is True

def test_list_all_drivers():
    drivers = list_all_drivers()
    assert "postgresql" in drivers
    assert "sqlite" in drivers

@patch("core.db.drivers.check_driver_installed", return_value=True)
def test_check_all_drivers(mock_check):
    status = check_all_drivers()
    assert status["postgresql"] is True
    assert status["sqlite"] is True

@patch("core.db.drivers.check_all_drivers")
@patch("builtins.print")
def test_print_driver_status(mock_print, mock_check_all):
    mock_check_all.return_value = {"postgresql": True, "oracle": False}
    print_driver_status()
    # Check that print was called multiple times correctly wrapping the tables
    assert mock_print.call_count > 5
