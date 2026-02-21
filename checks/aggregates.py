# This checks verifies aggregate values in specified columns
# between source and target datasets within a given tolerance.

import pandas as pd

from core.audit.enums import CheckStatus
from core.audit.result import TestResult
from typing import Optional


def _is_numeric_col(df: pd.DataFrame, column: str) -> bool:
    if column not in df.columns:
        return False
    # Check for numeric or boolean (which is technically numeric in pandas/numpy but usually not what we want for Sum/Avg?
    # User said int/float/bigint. Bool sums are count of True, which handles logic. I'll include it or just strict numeric.)
    # pd.api.types.is_numeric_dtype includes floats, ints, bools, complex.
    return pd.api.types.is_numeric_dtype(df[column])


def _check_all_nan(src_df: pd.DataFrame, tgt_df: pd.DataFrame, column: str, name: str, check_type: str) -> Optional[TestResult]:
    if not src_df.empty and pd.to_numeric(src_df[column], errors="coerce").isna().all():
        return TestResult(
            name=f"{check_type} Check: {name} - {column}",
            status=CheckStatus.WARN,
            message=f"Source column '{column}' in table '{name}' contains entirely NaN values.",
        )
    if not tgt_df.empty and pd.to_numeric(tgt_df[column], errors="coerce").isna().all():
        return TestResult(
            name=f"{check_type} Check: {name} - {column}",
            status=CheckStatus.WARN,
            message=f"Target column '{column}' in table '{name}' contains entirely NaN values.",
        )
    return None


def _is_id_col(column: str) -> bool:
    # Heuristic to identify PK/FK columns
    col_lower = column.lower()
    return col_lower == "id" or col_lower.endswith("_id") or col_lower.endswith("id")


def check_sum(
    src_df: pd.DataFrame, tgt_df: pd.DataFrame, column: str, name: str, tolerance: float
) -> Optional[TestResult]:
    # Restrict to numeric columns and exclude IDs
    if (
        not _is_numeric_col(src_df, column)
        or not _is_numeric_col(tgt_df, column)
        or _is_id_col(column)
    ):
        return None

    nan_check = _check_all_nan(src_df, tgt_df, column, name, "Sum")
    if nan_check:
        return nan_check

    # Use to_numeric with coerce to avoid crash on strings, but junk check will catch it separately
    src_vals = pd.to_numeric(src_df[column], errors="coerce").dropna()
    tgt_vals = pd.to_numeric(tgt_df[column], errors="coerce").dropna()

    src_sum = src_vals.sum()
    tgt_sum = tgt_vals.sum()

    if src_sum == 0:
        return TestResult(
            name=f"Sum Check: {name} - {column}",
            status=CheckStatus.WARN,
            message=f"Source sum for column '{column}' in table '{name}' is zero.",
        )

    diff = abs(src_sum - tgt_sum)
    pct_diff = (diff / src_sum) * 100 if src_sum > 0 else 0

    if pct_diff == 0:
        return TestResult(
            name=f"Sum Check: {name} - {column}",
            status=CheckStatus.PASS,
            message=f"Sum matches exactly for column '{column}' in table '{name}'. Source and Target both have sum {src_sum}.",
            details={"pct_difference": pct_diff},
        )
    elif pct_diff <= tolerance:
        return TestResult(
            name=f"Sum Check: {name} - {column}",
            status=CheckStatus.WARN,
            message=f"Sum difference within tolerance for column '{column}' in table '{name}'. Source: {src_sum}, Target: {tgt_sum}, Difference: {pct_diff:.2f}%.",
            details={"pct_difference": pct_diff},
        )
    else:
        return TestResult(
            name=f"Sum Check: {name} - {column}",
            status=CheckStatus.FAIL,
            message=f"Sum difference exceeds tolerance for column '{column}' in table '{name}'. Source: {src_sum}, Target: {tgt_sum}, Difference: {pct_diff:.2f}%.",
            details={"pct_difference": pct_diff},
        )


def check_avg(
    src_df: pd.DataFrame, tgt_df: pd.DataFrame, column: str, name: str, tolerance: float
) -> Optional[TestResult]:
    # Restrict to numeric columns and exclude IDs
    if (
        not _is_numeric_col(src_df, column)
        or not _is_numeric_col(tgt_df, column)
        or _is_id_col(column)
    ):
        return None

    nan_check = _check_all_nan(src_df, tgt_df, column, name, "Average")
    if nan_check:
        return nan_check

    src_vals = pd.to_numeric(src_df[column], errors="coerce").dropna()
    tgt_vals = pd.to_numeric(tgt_df[column], errors="coerce").dropna()

    src_avg = src_vals.mean() if not src_vals.empty else 0
    tgt_avg = tgt_vals.mean() if not tgt_vals.empty else 0

    if src_avg == 0:
        return TestResult(
            name=f"Average Check: {name} - {column}",
            status=CheckStatus.WARN,
            message=f"Source average for column '{column}' in table '{name}' is zero.",
        )

    diff = abs(src_avg - tgt_avg)
    pct_diff = (diff / src_avg) * 100 if src_avg > 0 else 0

    if pct_diff == 0:
        return TestResult(
            name=f"Average Check: {name} - {column}",
            status=CheckStatus.PASS,
            message=f"Average matches exactly for column '{column}' in table '{name}'. Source and Target both have average {src_avg}.",
            details={"pct_difference": pct_diff},
        )
    elif pct_diff <= tolerance:
        return TestResult(
            name=f"Average Check: {name} - {column}",
            status=CheckStatus.WARN,
            message=f"Average difference within tolerance for column '{column}' in table '{name}'. Source: {src_avg}, Target: {tgt_avg}, Difference: {pct_diff:.2f}%.",
            details={"pct_difference": pct_diff},
        )
    else:
        return TestResult(
            name=f"Average Check: {name} - {column}",
            status=CheckStatus.FAIL,
            message=f"Average difference exceeds tolerance for column '{column}' in table '{name}'. Source: {src_avg}, Target: {tgt_avg}, Difference: {pct_diff:.2f}%.",
            details={"pct_difference": pct_diff},
        )


def check_max(
    src_df: pd.DataFrame, tgt_df: pd.DataFrame, column: str, name: str, tolerance: float
) -> Optional[TestResult]:
    # Restrict to numeric columns and exclude IDs
    if (
        not _is_numeric_col(src_df, column)
        or not _is_numeric_col(tgt_df, column)
        or _is_id_col(column)
    ):
        return None

    nan_check = _check_all_nan(src_df, tgt_df, column, name, "Max")
    if nan_check:
        return nan_check

    src_vals = pd.to_numeric(src_df[column], errors="coerce").dropna()
    tgt_vals = pd.to_numeric(tgt_df[column], errors="coerce").dropna()

    src_max = src_vals.max() if not src_vals.empty else 0
    tgt_max = tgt_vals.max() if not tgt_vals.empty else 0

    if src_max == 0:
        return TestResult(
            name=f"Max Check: {name} - {column}",
            status=CheckStatus.WARN,
            message=f"Source max for column '{column}' in table '{name}' is zero.",
        )

    diff = abs(src_max - tgt_max)
    pct_diff = (diff / src_max) * 100 if src_max > 0 else 0

    if pct_diff == 0:
        return TestResult(
            name=f"Max Check: {name} - {column}",
            status=CheckStatus.PASS,
            message=f"Max matches exactly for column '{column}' in table '{name}'. Source and Target both have max {src_max}.",
            details={"pct_difference": pct_diff},
        )
    elif pct_diff <= tolerance:
        return TestResult(
            name=f"Max Check: {name} - {column}",
            status=CheckStatus.WARN,
            message=f"Max difference within tolerance for column '{column}' in table '{name}'. Source: {src_max}, Target: {tgt_max}, Difference: {pct_diff:.2f}%.",
            details={"pct_difference": pct_diff},
        )
    else:
        return TestResult(
            name=f"Max Check: {name} - {column}",
            status=CheckStatus.FAIL,
            message=f"Max difference exceeds tolerance for column '{column}' in table '{name}'. Source: {src_max}, Target: {tgt_max}, Difference: {pct_diff:.2f}%.",
            details={"pct_difference": pct_diff},
        )


def check_min(
    src_df: pd.DataFrame, tgt_df: pd.DataFrame, column: str, name: str, tolerance: float
) -> Optional[TestResult]:
    # Restrict to numeric columns and exclude IDs
    if (
        not _is_numeric_col(src_df, column)
        or not _is_numeric_col(tgt_df, column)
        or _is_id_col(column)
    ):
        return None

    nan_check = _check_all_nan(src_df, tgt_df, column, name, "Min")
    if nan_check:
        return nan_check

    src_vals = pd.to_numeric(src_df[column], errors="coerce").dropna()
    tgt_vals = pd.to_numeric(tgt_df[column], errors="coerce").dropna()

    src_min = src_vals.min() if not src_vals.empty else 0
    tgt_min = tgt_vals.min() if not tgt_vals.empty else 0

    if src_min == 0:
        return TestResult(
            name=f"Min Check: {name} - {column}",
            status=CheckStatus.WARN,
            message=f"Source min for column '{column}' in table '{name}' is zero.",
        )

    diff = abs(src_min - tgt_min)
    pct_diff = (diff / src_min) * 100 if src_min > 0 else 0

    if pct_diff == 0:
        return TestResult(
            name=f"Min Check: {name} - {column}",
            status=CheckStatus.PASS,
            message=f"Min matches exactly for column '{column}' in table '{name}'. Source and Target both have min {src_min}.",
            details={"pct_difference": pct_diff},
        )
    elif pct_diff <= tolerance:
        return TestResult(
            name=f"Min Check: {name} - {column}",
            status=CheckStatus.WARN,
            message=f"Min difference within tolerance for column '{column}' in table '{name}'. Source: {src_min}, Target: {tgt_min}, Difference: {pct_diff:.2f}%.",
            details={"pct_difference": pct_diff},
        )
    else:
        return TestResult(
            name=f"Min Check: {name} - {column}",
            status=CheckStatus.FAIL,
            message=f"Min difference exceeds tolerance for column '{column}' in table '{name}'. Source: {src_min}, Target: {tgt_min}, Difference: {pct_diff:.2f}%.",
            details={"pct_difference": pct_diff},
        )


def check_variance(
    src_df: pd.DataFrame, tgt_df: pd.DataFrame, column: str, name: str, tolerance: float
) -> Optional[TestResult]:
    # Restrict to numeric columns and exclude IDs
    if (
        not _is_numeric_col(src_df, column)
        or not _is_numeric_col(tgt_df, column)
        or _is_id_col(column)
    ):
        return None

    nan_check = _check_all_nan(src_df, tgt_df, column, name, "Variance")
    if nan_check:
        return nan_check

    src_vals = pd.to_numeric(src_df[column], errors="coerce").dropna()
    tgt_vals = pd.to_numeric(tgt_df[column], errors="coerce").dropna()

    src_var = src_vals.var() if not src_vals.empty else 0
    tgt_var = tgt_vals.var() if not tgt_vals.empty else 0

    if src_var == 0:
        return TestResult(
            name=f"Variance Check: {name} - {column}",
            status=CheckStatus.WARN,
            message=f"Source variance for column '{column}' in table '{name}' is zero.",
        )

    diff = abs(src_var - tgt_var)
    pct_diff = (diff / src_var) * 100 if src_var > 0 else 0

    if pct_diff == 0:
        return TestResult(
            name=f"Variance Check: {name} - {column}",
            status=CheckStatus.PASS,
            message=f"Variance matches exactly for column '{column}' in table '{name}'. Source and Target both have variance {src_var}.",
            details={"pct_difference": pct_diff},
        )
    elif pct_diff <= tolerance:
        return TestResult(
            name=f"Variance Check: {name} - {column}",
            status=CheckStatus.WARN,
            message=f"Variance difference within tolerance for column '{column}' in table '{name}'. Source: {src_var}, Target: {tgt_var}, Difference: {pct_diff:.2f}%.",
            details={"pct_difference": pct_diff},
        )
    else:
        return TestResult(
            name=f"Variance Check: {name} - {column}",
            status=CheckStatus.FAIL,
            message=f"Variance difference exceeds tolerance for column '{column}' in table '{name}'. Source: {src_var}, Target: {tgt_var}, Difference: {pct_diff:.2f}%.",
            details={"pct_difference": pct_diff},
        )
