import pytest
from unittest.mock import patch, MagicMock
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
    assert detect_db_type("mssql://server/db") == "mssql"
    assert detect_db_type("sqlserver://server/db") == "mssql"
    assert detect_db_type("oracle://server/db") == "oracle"
    assert detect_db_type("sqlite:///db.sqlite") == "sqlite"
    assert detect_db_type("unknown://server/db") is None

def test_check_driver_installed():
    # SQLite is built-in
    assert check_driver_installed("sqlite") is True
    # Unknown driver assumes fine
    assert check_driver_installed("unknown_db") is True

@patch("builtins.__import__")
def test_check_driver_installed_mocked(mock_import):
    # Simulate missing driver
    mock_import.side_effect = ImportError("No module named psycopg2")
    assert check_driver_installed("postgresql") is False

def test_get_installation_command():
    assert get_installation_command("postgresql") == "pip install psycopg2-binary"
    assert get_installation_command("unknown") == "Unknown driver"

def test_get_driver_info():
    info = get_driver_info("postgresql")
    assert info is not None
    assert info["driver"] == "psycopg2"
    assert get_driver_info("unknown") is None

@patch("core.db.drivers.check_driver_installed")
def test_validate_driver_or_raise(mock_check):
    # Test unknown DB type
    assert validate_driver_or_raise("unknown://uri") == ("unknown", True)

    # Test installed driver
    mock_check.return_value = True
    assert validate_driver_or_raise("postgresql://localhost") == ("postgresql", True)

    # Test missing driver
    mock_check.return_value = False
    with pytest.raises(DatabaseDriverError) as exc:
        validate_driver_or_raise("postgresql://localhost")
    assert "psycopg2" in str(exc.value)

def test_list_all_drivers():
    drivers = list_all_drivers()
    assert "postgresql" in drivers
    assert "sqlite" in drivers

@patch("core.db.drivers.check_all_drivers")
@patch("builtins.print")
def test_print_driver_status(mock_print, mock_check_all):
    mock_check_all.return_value = {"postgresql": False, "sqlite": True}
    print_driver_status()
    # Just verify it doesn't crash and calls print
    assert mock_print.call_count > 0
