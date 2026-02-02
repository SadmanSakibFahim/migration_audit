import pandas as pd
import pytest
from core.audit.enums import CheckStatus
from checks.data_constraints import check_data_constraints

def test_constraint_not_null_pass():
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "name": ["Alice", "Bob", "Charlie"]
    })
    constraints = {"name": ["not_null"]}
    result = check_data_constraints(df, constraints, "test_table")
    assert result.status == CheckStatus.PASS

def test_constraint_not_null_fail():
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "name": ["Alice", None, "Charlie"]
    })
    constraints = {"name": ["not_null"]}
    result = check_data_constraints(df, constraints, "test_table")
    assert result.status == CheckStatus.FAIL
    assert "null values" in result.message

def test_constraint_date_pass():
    df = pd.DataFrame({
        "created_at": ["2023-01-01", "2023-02-01"]
    })
    constraints = {"created_at": ["date"]}
    result = check_data_constraints(df, constraints, "test_table")
    assert result.status == CheckStatus.PASS

def test_constraint_date_fail():
    df = pd.DataFrame({
        "created_at": ["2023-01-01", "not-a-date"]
    })
    constraints = {"created_at": ["date"]}
    result = check_data_constraints(df, constraints, "test_table")
    assert result.status == CheckStatus.FAIL
    assert "invalid date values" in result.message

def test_constraint_multiple_fail():
    df = pd.DataFrame({
        "name": [None, "Bob"],
        "dob": ["not-a-date", "2020-01-01"]
    })
    constraints = {
        "name": ["not_null"],
        "dob": ["date"]
    }
    result = check_data_constraints(df, constraints, "test_table")
    assert result.status == CheckStatus.FAIL
    assert "Column 'name' has" in result.message
    assert "Column 'dob' has" in result.message

def test_constraint_multiple_pass():
    df = pd.DataFrame({
        "name": ["Alice", "Bob"],
        "dob": ["2020-01-01", "2022-02-02"]
    })
    constraints = {
        "name": ["not_null"],
        "dob": ["date", "not_null"]
    }
    result = check_data_constraints(df, constraints, "test_table")
    assert result.status == CheckStatus.PASS
