from core.audit.result import TestResult
import pandas as pd
from core.audit.enums import CheckStatus
from typing import Dict, List

# This function checks whether each primary key
# has data in each column without which the data is incomplete.

def check_data_constraints(df: pd.DataFrame, columns: Dict[str, List[str]], name: str) -> TestResult:
    # Guard: None or empty DataFrame
    if df is None or not isinstance(df, pd.DataFrame):
        return TestResult(
            name=f"Data Constraints Check: {name}",
            status=CheckStatus.FAIL,
            message=f"Cannot run data constraints check — DataFrame is None or invalid for table '{name}'.",
        )
    if df.empty:
        return TestResult(
            name=f"Data Constraints Check: {name}",
            status=CheckStatus.WARN,
            message=f"DataFrame is empty for table '{name}' — data constraints check skipped.",
        )

    issues = []
    total_rows = len(df)

    for column, constraints in columns.items():
        if 'not_null' in constraints:
            null_count = df[df[column].isnull()].shape[0]
            if null_count > 0:
                issues.append(f"Column '{column}' has {null_count} null values out of {total_rows} rows.")

        if 'date' in constraints:
            invalid_dates = df[~pd.to_datetime(df[column], errors='coerce').notnull()]
            invalid_count = invalid_dates.shape[0]
            if invalid_count > 0:
                issues.append(f"Column '{column}' has {invalid_count} invalid date values out of {total_rows} rows.")

    display_name = name
    if len(columns) == 1:
        display_name = f"{name}.{list(columns.keys())[0]}"

    if not issues:
        return TestResult(
            name=f"Data Constraints Check: {display_name}",
            status=CheckStatus.PASS,
            message=f"All data constraints are satisfied for table '{name}'."
        )       
    
    else:
        return TestResult(
            name=f"Data Constraints Check: {display_name}",
            status=CheckStatus.FAIL,
            message=f"Data constraint issues found in table '{name}': " + "; ".join(issues),
            details={"issues": issues}
        )
