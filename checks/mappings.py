# This checks whether mapping definitions between source and target datasets
# are consistent and correctly defined.

from core.audit.result import TestResult
from core.audit.enums import CheckStatus
import pandas as pd
from typing import List

def check_mappings(df: pd.DataFrame, columns: List[str], allowed_values: List[str], name: str) -> TestResult:
    issues = []
    for column in columns:
        if column not in df.columns:
            issues.append(f"Column '{column}' is missing in table '{name}'.")
            continue

        invalid_values = df[~df[column].isin(allowed_values)][column].unique()
        if len(invalid_values) > 0:
            issues.append(f"Column '{column}' in table '{name}' has invalid values: {invalid_values}.")

    if not issues:
        return TestResult(
            name=f"Mapping Check: {name}",
            status=CheckStatus.PASS,
            message=f"All mappings are valid for table '{name}'."
        )
    else:
        return TestResult(
            name=f"Mapping Check: {name}",
            status=CheckStatus.FAIL,
            message=f"Mapping issues found in table '{name}': " + "; ".join(issues),
            details = {"issues": issues}
        )