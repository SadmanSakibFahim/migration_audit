# This function validates data completeness
# by comparing row counts between source and target datasets.
from typing import Optional

import pandas as pd

from core.audit.enums import CheckStatus
from core.audit.result import TestResult


def check_volume(
    name: str,
    src_df: pd.DataFrame,
    tgt_df: pd.DataFrame,
    tolerance_pct: float = 0.0,
    mapping_type: Optional[str] = None,
    expected_ratio: Optional[float] = None,
) -> TestResult:
    """
    Validates data volume (row count) between source and target.

    Args:
        name: Table name for logging
        src_df: Source DataFrame
        tgt_df: Target DataFrame
        tolerance_pct: Acceptable loss percentage (0-100)
        mapping_type: Type of mapping ('1:1', '1:N', 'N:1', 'N:M')
        expected_ratio: Expected ratio of target_rows / source_rows
    """
    src_count = len(src_df)
    tgt_count = len(tgt_df)

    # 1. Handle case where both are empty (Success)
    if src_count == 0 and tgt_count == 0:
        return TestResult(
            name=f"Volume Check: {name}",
            status=CheckStatus.PASS,
            message=f"Both source and target datasets for '{name}' are empty. This is considered a consistent migration.",
            metrics={
                "src_rows": 0,
                "tgt_rows": 0,
                "difference": 0,
                "tolerance": tolerance_pct,
            },
        )

    # 2. Handle case where only source is empty (Warning)
    if src_count == 0:
        return TestResult(
            name=f"Volume Check: {name}",
            status=CheckStatus.WARN,
            message=f"Source data for table '{name}' has zero rows, but target has {tgt_count} rows.",
            metrics={
                "src_rows": 0,
                "tgt_rows": tgt_count,
                "difference": tgt_count,
                "tolerance": tolerance_pct,
            },
        )

    # For complex mappings, adjust expectations
    if mapping_type == "1:N" and expected_ratio:
        expected_tgt_count = int(src_count * expected_ratio)
        diff = abs(tgt_count - expected_tgt_count)
        loss_pct = (diff / expected_tgt_count) * 100 if expected_tgt_count > 0 else 0
        comparison_msg = (
            f"Expected ~{expected_tgt_count} target rows (ratio {expected_ratio:.2f})"
        )
    elif mapping_type == "N:1" and expected_ratio:
        expected_tgt_count = int(src_count * expected_ratio)
        diff = abs(tgt_count - expected_tgt_count)
        loss_pct = (diff / expected_tgt_count) * 100 if expected_tgt_count > 0 else 0
        comparison_msg = (
            f"Expected ~{expected_tgt_count} target rows (ratio {expected_ratio:.2f})"
        )
    else:
        # Standard 1:1 comparison
        diff = abs(src_count - tgt_count)
        loss_pct = (diff / src_count) * 100 if src_count > 0 else 0
        comparison_msg = ""

    metrics = {
        "src_rows": src_count,
        "tgt_rows": tgt_count,
        "difference": diff,
        "tolerance": tolerance_pct,
    }

    if loss_pct == 0:
        msg = f"Row counts match exactly for table '{name}'. Source: {src_count}, Target: {tgt_count} rows."
        if comparison_msg:
            msg += f" {comparison_msg}"
        return TestResult(
            name=f"Volume Check: {name}",
            status=CheckStatus.PASS,
            message=msg,
            metrics=metrics,
        )
    elif loss_pct <= tolerance_pct:
        msg = f"Row count difference within tolerance for table '{name}'. Source: {src_count}, Target: {tgt_count}, Difference: {loss_pct:.2f}%."
        if comparison_msg:
            msg += f" {comparison_msg}"
        return TestResult(
            name=f"Volume Check: {name}",
            status=CheckStatus.PASS,
            message=msg,
            metrics=metrics,
        )
    else:
        msg = f"Row count difference exceeds tolerance for table '{name}'. Source: {src_count}, Target: {tgt_count}, Difference: {loss_pct:.2f}%."
        if comparison_msg:
            msg += f" {comparison_msg}"
        return TestResult(
            name=f"Volume Check: {name}",
            status=CheckStatus.FAIL,
            message=msg,
            metrics=metrics,
        )
