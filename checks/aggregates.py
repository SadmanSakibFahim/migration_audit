# This checks verifies aggregate values in specified columns
# between source and target datasets within a given tolerance.

# add type hints all over the code
from core.result import TestResult
from core.enums import CheckStatus
import pandas as pd

# add type hints all over the code
def check_sum(src_df: pd.DataFrame, tgt_df: pd.DataFrame, column: str, name: str, tolerance: float) -> TestResult:
    src_sum = src_df[column].dropna().sum()
    tgt_sum = tgt_df[column].dropna().sum()

    if src_sum == 0:
        return TestResult(
            name=f"Sum Check: {name} - {column}",
            status=CheckStatus.WARN,
            message=f"Source sum for column '{column}' in table '{name}' is zero."
        )

    diff = abs(src_sum - tgt_sum)
    pct_diff = (diff / src_sum) * 100 if src_sum > 0 else 0

    if pct_diff == 0:
        return TestResult(
            name=f"Sum Check: {name} - {column}",
            status=CheckStatus.PASS,
            message=f"Sum matches exactly for column '{column}' in table '{name}'. Source and Target both have sum {src_sum}.",
            details={"pct_difference": pct_diff}
        )
    elif pct_diff <= tolerance:
        return TestResult(
            name=f"Sum Check: {name} - {column}",
            status=CheckStatus.WARN,
            message=f"Sum difference within tolerance for column '{column}' in table '{name}'. Source: {src_sum}, Target: {tgt_sum}, Difference: {pct_diff:.2f}%.",
            details={"pct_difference": pct_diff}
        )
    else:
        return TestResult(
            name=f"Sum Check: {name} - {column}",
            status=CheckStatus.FAIL,
            message=f"Sum difference exceeds tolerance for column '{column}' in table '{name}'. Source: {src_sum}, Target: {tgt_sum}, Difference: {pct_diff:.2f}%.",
            details={"pct_difference": pct_diff}
        )
    
def check_avg(src_df: pd.DataFrame, tgt_df: pd.DataFrame, column: str, name: str, tolerance: float) -> TestResult:
    src_avg = src_df[column].dropna().mean()
    tgt_avg = tgt_df[column].dropna().mean()

    if src_avg == 0:
        return TestResult(
            name=f"Average Check: {name} - {column}",
            status=CheckStatus.WARN,
            message=f"Source average for column '{column}' in table '{name}' is zero."
        )

    diff = abs(src_avg - tgt_avg)
    pct_diff = (diff / src_avg) * 100 if src_avg > 0 else 0

    if pct_diff == 0:
        return TestResult(
            name=f"Average Check: {name} - {column}",
            status=CheckStatus.PASS,
            message=f"Average matches exactly for column '{column}' in table '{name}'. Source and Target both have average {src_avg}.",
            details={"pct_difference": pct_diff}
        )
    elif pct_diff <= tolerance:
        return TestResult(
            name=f"Average Check: {name} - {column}",
            status=CheckStatus.WARN,
            message=f"Average difference within tolerance for column '{column}' in table '{name}'. Source: {src_avg}, Target: {tgt_avg}, Difference: {pct_diff:.2f}%.",
            details={"pct_difference": pct_diff}
        )
    else:
        return TestResult(
            name=f"Average Check: {name} - {column}",
            status=CheckStatus.FAIL,
            message=f"Average difference exceeds tolerance for column '{column}' in table '{name}'. Source: {src_avg}, Target: {tgt_avg}, Difference: {pct_diff:.2f}%.",
            details={"pct_difference": pct_diff}
        )
    
def check_max(src_df: pd.DataFrame, tgt_df: pd.DataFrame, column: str, name: str, tolerance: float) -> TestResult:
    src_max = src_df[column].dropna().max()
    tgt_max = tgt_df[column].dropna().max()

    if src_max == 0:
        return TestResult(
            name=f"Max Check: {name} - {column}",
            status=CheckStatus.WARN,
            message=f"Source max for column '{column}' in table '{name}' is zero."
        )

    diff = abs(src_max - tgt_max)
    pct_diff = (diff / src_max) * 100 if src_max > 0 else 0

    if pct_diff == 0:
        return TestResult(
            name=f"Max Check: {name} - {column}",
            status=CheckStatus.PASS,
            message=f"Max matches exactly for column '{column}' in table '{name}'. Source and Target both have max {src_max}.",
            details={"pct_difference": pct_diff}
        )
    elif pct_diff <= tolerance:
        return TestResult(
            name=f"Max Check: {name} - {column}",
            status=CheckStatus.WARN,
            message=f"Max difference within tolerance for column '{column}' in table '{name}'. Source: {src_max}, Target: {tgt_max}, Difference: {pct_diff:.2f}%.",
            details={"pct_difference": pct_diff}
        )
    else:
        return TestResult(
            name=f"Max Check: {name} - {column}",
            status=CheckStatus.FAIL,
            message=f"Max difference exceeds tolerance for column '{column}' in table '{name}'. Source: {src_max}, Target: {tgt_max}, Difference: {pct_diff:.2f}%.",
            details={"pct_difference": pct_diff}
        )
    
def check_min(src_df: pd.DataFrame, tgt_df: pd.DataFrame, column: str, name: str, tolerance: float) -> TestResult:
    src_min = src_df[column].dropna().min()
    tgt_min = tgt_df[column].dropna().min()

    if src_min == 0:
        return TestResult(
            name=f"Min Check: {name} - {column}",
            status=CheckStatus.WARN,
            message=f"Source min for column '{column}' in table '{name}' is zero."
        )

    diff = abs(src_min - tgt_min)
    pct_diff = (diff / src_min) * 100 if src_min > 0 else 0

    if pct_diff == 0:
        return TestResult(
            name=f"Min Check: {name} - {column}",
            status=CheckStatus.PASS,
            message=f"Min matches exactly for column '{column}' in table '{name}'. Source and Target both have min {src_min}.",
            details={"pct_difference": pct_diff}
        )
    elif pct_diff <= tolerance:
        return TestResult(
            name=f"Min Check: {name} - {column}",
            status=CheckStatus.WARN,
            message=f"Min difference within tolerance for column '{column}' in table '{name}'. Source: {src_min}, Target: {tgt_min}, Difference: {pct_diff:.2f}%.",
            details={"pct_difference": pct_diff}
        )
    else:
        return TestResult(
            name=f"Min Check: {name} - {column}",
            status=CheckStatus.FAIL,
            message=f"Min difference exceeds tolerance for column '{column}' in table '{name}'. Source: {src_min}, Target: {tgt_min}, Difference: {pct_diff:.2f}%.",
            details={"pct_difference": pct_diff}
        )
    
def check_variance(src_df: pd.DataFrame, tgt_df: pd.DataFrame, column: str, name: str, tolerance: float) -> TestResult:
    src_var = src_df[column].dropna().var()
    tgt_var = tgt_df[column].dropna().var()

    if src_var == 0:
        return TestResult(
            name=f"Variance Check: {name} - {column}",
            status=CheckStatus.WARN,
            message=f"Source variance for column '{column}' in table '{name}' is zero."
        )

    diff = abs(src_var - tgt_var)
    pct_diff = (diff / src_var) * 100 if src_var > 0 else 0

    if pct_diff == 0:
        return TestResult(
            name=f"Variance Check: {name} - {column}",
            status=CheckStatus.PASS,
            message=f"Variance matches exactly for column '{column}' in table '{name}'. Source and Target both have variance {src_var}.",
            details={"pct_difference": pct_diff}
        )
    elif pct_diff <= tolerance:
        return TestResult(
            name=f"Variance Check: {name} - {column}",
            status=CheckStatus.WARN,
            message=f"Variance difference within tolerance for column '{column}' in table '{name}'. Source: {src_var}, Target: {tgt_var}, Difference: {pct_diff:.2f}%.",
            details={"pct_difference": pct_diff}
        )
    else:
        return TestResult(
            name=f"Variance Check: {name} - {column}",
            status=CheckStatus.FAIL,
            message=f"Variance difference exceeds tolerance for column '{column}' in table '{name}'. Source: {src_var}, Target: {tgt_var}, Difference: {pct_diff:.2f}%.",
            details={"pct_difference": pct_diff}
        )