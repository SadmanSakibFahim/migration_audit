# This function validates data completeness
# by comparing row counts between source and target datasets.
import pandas as pd
from core.result import TestResult
from core.enums import CheckStatus
from typing import Optional

def check_volume(
    name: str, 
    src_df: pd.DataFrame, 
    tgt_df: pd.DataFrame, 
    tolerance_pct: float = 0.0,
    mapping_type: Optional[str] = None,
    expected_ratio: Optional[float] = None
) -> TestResult:
    """
    Validates data volume (row count) between source and target.
    
    Args:
        name: Table name for logging
        src_df: Source DataFrame (may be merged from multiple sources)
        tgt_df: Target DataFrame (may be merged from multiple targets)
        tolerance_pct: Acceptable loss percentage (0-100)
        mapping_type: Type of mapping ('1:1', '1:N', 'N:1', 'N:M') for context
        expected_ratio: Expected ratio of target_rows / source_rows (for 1:N or N:1 mappings)
    """
    src_count = len(src_df)
    tgt_count = len(tgt_df)

    # #region agent log
    import json
    try:
        with open('.cursor\\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"checks/volume.py:27","message":"Volume check entry","data":{"name":name,"src_count":src_count,"tgt_count":tgt_count,"mapping_type":mapping_type},"timestamp":int(__import__('time').time()*1000)}) + '\n')
    except: pass
    # #endregion

    if src_count == 0:
        return TestResult(
            name=f"Volume Check: {name}",
            status=CheckStatus.WARN,
            message=f"Source data for table '{name}' has zero rows."
        )

    # For complex mappings, adjust expectations
    if mapping_type == '1:N' and expected_ratio:
        # For 1:N, we expect more target rows
        expected_tgt_count = int(src_count * expected_ratio)
        diff = abs(tgt_count - expected_tgt_count)
        loss_pct = (diff / expected_tgt_count) * 100 if expected_tgt_count > 0 else 0
        comparison_msg = f"Expected ~{expected_tgt_count} target rows (ratio {expected_ratio:.2f})"
    elif mapping_type == 'N:1' and expected_ratio:
        # For N:1, we expect fewer target rows
        expected_tgt_count = int(src_count * expected_ratio)
        diff = abs(tgt_count - expected_tgt_count)
        loss_pct = (diff / expected_tgt_count) * 100 if expected_tgt_count > 0 else 0
        comparison_msg = f"Expected ~{expected_tgt_count} target rows (ratio {expected_ratio:.2f})"
    else:
        # Standard 1:1 comparison
        diff = abs(src_count - tgt_count)
        loss_pct = (diff / src_count) * 100 if src_count > 0 else 0
        comparison_msg = ""

    if loss_pct == 0:
        msg = f"Row counts match exactly for table '{name}'. Source: {src_count}, Target: {tgt_count} rows."
        if comparison_msg:
            msg += f" {comparison_msg}"
        return TestResult(
            name=f"Volume Check: {name}",
            status=CheckStatus.PASS,
            message=msg
        )
    elif loss_pct <= tolerance_pct:
        msg = f"Row count difference within tolerance for table '{name}'. Source: {src_count}, Target: {tgt_count}, Difference: {loss_pct:.2f}%."
        if comparison_msg:
            msg += f" {comparison_msg}"
        return TestResult(
            name=f"Volume Check: {name}",
            status=CheckStatus.WARN,
            message=msg
        )
    else:
        msg = f"Row count difference exceeds tolerance for table '{name}'. Source: {src_count}, Target: {tgt_count}, Difference: {loss_pct:.2f}%."
        if comparison_msg:
            msg += f" {comparison_msg}"
        return TestResult(
            name=f"Volume Check: {name}",
            status=CheckStatus.FAIL,
            message=msg
        )