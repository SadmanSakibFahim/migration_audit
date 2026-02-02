import pandas as pd
import pytest
from core.audit.enums import CheckStatus
from checks.mappings import check_mappings

def test_check_mappings_pass():
    """Test that valid mappings pass."""
    df = pd.DataFrame({
        "status": ["active", "inactive", "active"],
        "code": ["A", "B", "A"]
    })
    
    # Check status column
    result = check_mappings(df, ["status"], ["active", "inactive"], "test_table")
    assert result.status == CheckStatus.PASS
    assert "All mappings are valid" in result.message

def test_check_mappings_fail_invalid_value():
    """Test that invalid values cause failure."""
    df = pd.DataFrame({
        "status": ["active", "INVALID_VALUE", "active"]
    })
    
    result = check_mappings(df, ["status"], ["active", "inactive"], "test_table")
    assert result.status == CheckStatus.FAIL
    assert "invalid values" in result.message
    assert "INVALID_VALUE" in str(result.message)

def test_check_mappings_fail_missing_column():
    """Test that missing column causes issue."""
    df = pd.DataFrame({
        "other_col": [1, 2, 3]
    })
    
    result = check_mappings(df, ["status"], ["active", "inactive"], "test_table")
    assert result.status == CheckStatus.FAIL
    assert "Column 'status' is missing" in result.message

def test_check_mappings_multiple_columns_mixed_results():
    """Test checking multiple columns where one fails."""
    df = pd.DataFrame({
        "status": ["active", "active"],
        "type": ["A", "INVALID_TYPE"]
    })
    
    result = check_mappings(df, ["status", "type"], ["active", "A", "B"], "test_table")
    # Note: The function check_mappings takes a list of allowed values that applies to *all* columns passed in check?
    # Let's check the implementation of checks/mappings.py.
    # It takes `columns: List[str]` and `allowed_values: List[str]`. 
    # This implies the same allowed_values list is applied to ALL columns in that list.
    
    assert result.status == CheckStatus.FAIL
    assert "Column 'type' in table 'test_table' has invalid values" in result.message
    # status column should rely on same allowed_values, so "active" must be in allowed_values.
