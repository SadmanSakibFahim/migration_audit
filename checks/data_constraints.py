from typing import Dict, List

import pandas as pd

from core.audit.enums import CheckStatus
from core.audit.result import TestResult

# This function checks whether each primary key
# has data in each column without which the data is incomplete.


def check_data_constraints(
    df: pd.DataFrame, columns: Dict[str, List[str]], name: str
) -> TestResult:
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
        if "not_null" in constraints:
            null_count = df[df[column].isnull()].shape[0]
            if null_count > 0:
                issues.append(
                    f"Column '{column}' has {null_count} null values out of {total_rows} rows."
                )

        if "date" in constraints:
            invalid_dates = df[~pd.to_datetime(df[column], errors="coerce").notnull()]
            invalid_count = invalid_dates.shape[0]
            if invalid_count > 0:
                issues.append(
                    f"Column '{column}' has {invalid_count} invalid date values out of {total_rows} rows."
                )

    display_name = name
    if len(columns) == 1:
        display_name = f"{name}.{list(columns.keys())[0]}"

    if not issues:
        return TestResult(
            name=f"Data Constraints Check: {display_name}",
            status=CheckStatus.PASS,
            message=f"All data constraints are satisfied for table '{name}'.",
        )

    else:
        return TestResult(
            name=f"Data Constraints Check: {display_name}",
            status=CheckStatus.FAIL,
            message=f"Data constraint issues found in table '{name}': "
            + "; ".join(issues),
            details={"issues": issues},
        )

def check_uniqueness(
    src_df: pd.DataFrame,
    tgt_df: pd.DataFrame,
    column: str,
    name: str
) -> List[TestResult]:
    """
    Compare uniqueness (nunique / count) ratio between source and target.
    Detects if a column that was unique (or highly unique) in source received duplicated data in target.
    """
    results: List[TestResult] = []
    check_name = f"Uniqueness Check: {name} - {column}"

    if column not in src_df.columns or column not in tgt_df.columns:
        results.append(TestResult(
            name=check_name, status=CheckStatus.FAIL, 
            message=f"Column '{column}' missing from source or target."
        ))
        return results

    src_count = src_df[column].count()
    tgt_count = tgt_df[column].count()

    if src_count == 0:
        results.append(TestResult(name=check_name, status=CheckStatus.WARN, message=f"Column '{column}' is empty in source."))
        return results

    src_unique = src_df[column].nunique()
    tgt_unique = tgt_df[column].nunique()

    src_ratio = src_unique / src_count
    tgt_ratio = tgt_unique / tgt_count if tgt_count > 0 else 0.0

    details = {
        "src_unique_ratio": round(src_ratio, 5),
        "tgt_unique_ratio": round(tgt_ratio, 5),
        "src_unique_count": int(src_unique),
        "tgt_unique_count": int(tgt_unique),
    }

    if tgt_ratio < src_ratio - 0.001:  # Allow tiny floating precision tolerance
        results.append(TestResult(
            name=check_name, status=CheckStatus.FAIL,
            message=f"Loss of uniqueness in column '{column}'. Source ratio ({src_ratio:.4f}) dropped to Target ratio ({tgt_ratio:.4f}). Migration likely introduced duplicates.",
            details=details
        ))
    else:
        results.append(TestResult(
            name=check_name, status=CheckStatus.PASS,
            message=f"Uniqueness constraint preserved for column '{column}'.",
            details=details
        ))

    return results
