# checks/null_sentinel_checks.py
# Sheldon Cooper: "NULL, zero, -1, and 'N/A' are not semantically equivalent.
# Yet here we are, writing a check to accommodate people who think they are."
# Leonard Hofstadter: This is actually a really common real-world problem. Just implement it.

from typing import Any, List

import pandas as pd

from core.audit.enums import CheckStatus
from core.audit.result import TestResult


def _normalize_sentinels(series: pd.Series, sentinels: List[Any]) -> pd.Series:
    """Replace all sentinel values (and already-null values) with pd.NA."""
    result = series.copy()
    # Convert sentinels to the same type as values where possible
    for s in sentinels:
        # Handle empty string sentinel
        if isinstance(s, str) and s == "":
            result = result.replace("", pd.NA)
        else:
            result = result.replace(s, pd.NA)
    return result


def check_null_sentinel_equivalence(
    src_df: pd.DataFrame,
    tgt_df: pd.DataFrame,
    column: str,
    name: str,
    sentinels: List[Any],
) -> List[TestResult]:
    """
    Detect null/sentinel value inconsistencies between source and target.

    Normalizes a user-declared list of sentinel values (e.g. 0, -1, 'N/A', '')
    to None on both sides, then compares null rates before and after normalization.

    Possible outcomes:
    - PASS: null rates match after normalization (logically equivalent, just different representation).
    - WARN: null rates didn't match before normalization but match after (sentinel substitution occurred).
    - FAIL: null rates still don't match even after normalization (data loss / corrupt nulls).

    Args:
        src_df: Source DataFrame.
        tgt_df: Target DataFrame.
        column: The column name to check.
        name: Table name (for result labeling).
        sentinels: List of values to treat as null equivalents.
                   e.g. [0, -1, "N/A", "", "NULL", "null"]

    Returns:
        List of TestResult objects.
    """
    results: List[TestResult] = []
    check_name = f"Null/Sentinel Check: {name} - {column}"

    # Guard: column existence
    if column not in src_df.columns:
        results.append(TestResult(
            name=check_name,
            status=CheckStatus.FAIL,
            message=f"Column '{column}' not found in source table '{name}'.",
        ))
        return results

    if column not in tgt_df.columns:
        results.append(TestResult(
            name=check_name,
            status=CheckStatus.FAIL,
            message=f"Column '{column}' not found in target table '{name}'.",
        ))
        return results

    src_series = src_df[column]
    tgt_series = tgt_df[column]

    src_total = len(src_series)
    tgt_total = len(tgt_series)

    if src_total == 0 or tgt_total == 0:
        results.append(TestResult(
            name=check_name,
            status=CheckStatus.WARN,
            message=f"Column '{column}' in '{name}' is empty on one or both sides — sentinel check skipped.",
        ))
        return results

    # --- Raw null rates (before normalization) ---
    src_null_before = int(src_series.isna().sum())
    tgt_null_before = int(tgt_series.isna().sum())
    src_null_rate_before = src_null_before / src_total
    tgt_null_rate_before = tgt_null_before / tgt_total

    # --- Normalize sentinels ---
    src_normalized = _normalize_sentinels(src_series, sentinels)
    tgt_normalized = _normalize_sentinels(tgt_series, sentinels)

    src_null_after = int(src_normalized.isna().sum())
    tgt_null_after = int(tgt_normalized.isna().sum())
    src_null_rate_after = src_null_after / src_total
    tgt_null_rate_after = tgt_null_after / tgt_total

    # Count how many sentinel substitutions happened on each side
    src_sentinel_count = src_null_after - src_null_before
    tgt_sentinel_count = tgt_null_after - tgt_null_before

    details = {
        "sentinels_declared": [str(s) for s in sentinels],
        "src_row_count": src_total,
        "tgt_row_count": tgt_total,
        "src_null_rate_before": round(src_null_rate_before * 100, 2),
        "tgt_null_rate_before": round(tgt_null_rate_before * 100, 2),
        "src_null_rate_after": round(src_null_rate_after * 100, 2),
        "tgt_null_rate_after": round(tgt_null_rate_after * 100, 2),
        "src_sentinel_substitutions": src_sentinel_count,
        "tgt_sentinel_substitutions": tgt_sentinel_count,
    }

    # --- Decision logic ---
    rates_match_before = abs(src_null_rate_before - tgt_null_rate_before) < 0.001
    rates_match_after = abs(src_null_rate_after - tgt_null_rate_after) < 0.001

    if rates_match_before and rates_match_after:
        # Perfect: no sentinel chaos at all
        results.append(TestResult(
            name=check_name,
            status=CheckStatus.PASS,
            message=(
                f"Null/sentinel rates match consistently for column '{column}' in '{name}'. "
                f"Null rate: {src_null_rate_before*100:.1f}% (source) vs "
                f"{tgt_null_rate_before*100:.1f}% (target). "
                f"Sentinels substituted: src={src_sentinel_count}, tgt={tgt_sentinel_count}."
            ),
            details=details,
        ))
    elif not rates_match_before and rates_match_after:
        # The migration changed the physical representation (sentinel → NULL) but data is logically equivalent
        results.append(TestResult(
            name=check_name,
            status=CheckStatus.WARN,
            message=(
                f"Null representation changed in column '{column}' of '{name}' "
                f"(logically equivalent after sentinel normalization). "
                f"Before normalization: src={src_null_rate_before*100:.1f}%, tgt={tgt_null_rate_before*100:.1f}%. "
                f"After normalization: both {src_null_rate_after*100:.1f}%. "
                f"Sentinels substituted — src: {src_sentinel_count} rows, tgt: {tgt_sentinel_count} rows. "
                f"This is usually intentional but worth confirming."
            ),
            details=details,
        ))
    elif rates_match_before and not rates_match_after:
        # Rare: rates matched before but normalization made them diverge — sentinel list is inconsistent
        results.append(TestResult(
            name=check_name,
            status=CheckStatus.WARN,
            message=(
                f"Sentinel normalization introduced a null rate divergence in column '{column}' of '{name}'. "
                f"This suggests the declared sentinel list may be asymmetric across source and target. "
                f"Before: src={src_null_rate_before*100:.1f}% vs tgt={tgt_null_rate_before*100:.1f}% (matched). "
                f"After: src={src_null_rate_after*100:.1f}% vs tgt={tgt_null_rate_after*100:.1f}% (diverged). "
                f"Review your sentinel declarations."
            ),
            details=details,
        ))
    else:
        # Neither raw nor normalized rates match — genuine data integrity issue
        diff_pct = abs(src_null_rate_after - tgt_null_rate_after) * 100
        results.append(TestResult(
            name=check_name,
            status=CheckStatus.FAIL,
            message=(
                f"Null/sentinel mismatch in column '{column}' of '{name}' even after normalization. "
                f"Normalized null rates differ by {diff_pct:.1f}%: "
                f"src={src_null_rate_after*100:.1f}% vs tgt={tgt_null_rate_after*100:.1f}%. "
                f"Raw rates: src={src_null_rate_before*100:.1f}% vs tgt={tgt_null_rate_before*100:.1f}%. "
                f"This suggests genuine data loss or incorrect NULL handling during migration."
            ),
            details=details,
        ))

    return results
