# This function validates data completeness
# by comparing row counts between source and target datasets.
import pandas as pd
from core.result import TestResult
from core.enums import CheckStatus

def check_volume(name: str, src_df: pd.DataFrame, tgt_df: pd.DataFrame, tolerance_pct: float = 0.0) -> TestResult:
    src_count = len(src_df)
    tgt_count = len(tgt_df)

    if src_count == 0:
        return TestResult(
            name=f"Volume Check: {name}",
            status=CheckStatus.WARN,
            message=f"Source table '{name}' has zero rows."
        )

    diff = abs(src_count - tgt_count)
    loss_pct = (diff / src_count) * 100 if src_count > 0 else 0

    if loss_pct == 0:
        return TestResult(
            name=f"Volume Check: {name}",
            status=CheckStatus.PASS,
            message=f"Row counts match exactly for table '{name}'. Source and Target both have {src_count} rows."
        )
    elif loss_pct <= tolerance_pct:
        return TestResult(
            name=f"Volume Check: {name}",
            status=CheckStatus.WARN,
            message=f"Row count difference within tolerance for table '{name}'. Source: {src_count}, Target: {tgt_count}, Loss: {loss_pct:.2f}%."
        )
    else:
        return TestResult(
            name=f"Volume Check: {name}",
            status=CheckStatus.FAIL,
            message=f"Row count difference exceeds tolerance for table '{name}'. Source: {src_count}, Target: {tgt_count}, Loss: {loss_pct:.2f}%."
        )