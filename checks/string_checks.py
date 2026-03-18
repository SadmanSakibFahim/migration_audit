# checks/string_checks.py

from typing import List, Optional

import pandas as pd

from core.audit.enums import CheckStatus
from core.audit.result import TestResult


def check_string_truncation(
    src_df: pd.DataFrame,
    tgt_df: pd.DataFrame,
    column: str,
    name: str,
    max_length: Optional[int] = None,
) -> List[TestResult]:
    """
    Detect silent string truncation between source and target columns.

    Args:
        src_df: Source DataFrame.
        tgt_df: Target DataFrame.
        column: The column name to check.
        name: Table name (for result labeling).
        max_length: Optional declared max length of the target column (e.g. VARCHAR(255)).
                    If not provided, uses max observed length in target as proxy.

    Returns:
        List of TestResult objects.
    """
    results: List[TestResult] = []
    check_name = f"String Truncation Check: {name} - {column}"

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

    # Compute string lengths (coerce non-strings gracefully)
    src_lengths = src_df[column].dropna().astype(str).str.len()
    tgt_lengths = tgt_df[column].dropna().astype(str).str.len()

    if src_lengths.empty:
        results.append(TestResult(
            name=check_name,
            status=CheckStatus.WARN,
            message=f"Source column '{column}' in '{name}' is empty or all-null — skipping truncation check.",
        ))
        return results

    src_max = int(src_lengths.max())
    tgt_max = int(tgt_lengths.max()) if not tgt_lengths.empty else 0

    effective_limit = max_length if max_length is not None else tgt_max

    # Count source rows that would be truncated
    truncated_count = int((src_lengths > effective_limit).sum()) if effective_limit > 0 else 0

    details = {
        "src_max_length": src_max,
        "tgt_max_length": tgt_max,
        "declared_max_length": max_length,
        "effective_limit": effective_limit,
        "rows_exceeding_limit": truncated_count,
        "src_row_count": len(src_lengths),
    }

    if truncated_count > 0:
        pct = (truncated_count / len(src_lengths)) * 100
        sample_values = (
            src_df.loc[src_df[column].dropna().astype(str).str.len() > effective_limit, column]
            .head(3)
            .tolist()
        )
        results.append(TestResult(
            name=check_name,
            status=CheckStatus.FAIL,
            message=(
                f"TRUNCATION DETECTED: {truncated_count} rows ({pct:.1f}%) in source column "
                f"'{column}' exceed the effective limit of {effective_limit} chars "
                f"(src_max={src_max}, tgt_max={tgt_max}). "
                f"Sample values: {sample_values}"
            ),
            details={**details, "sample_values": sample_values},
        ))
    elif src_max > tgt_max and tgt_max > 0:
        # Source had longer values historically but current rows fit — borderline warning
        results.append(TestResult(
            name=check_name,
            status=CheckStatus.WARN,
            message=(
                f"Source column '{column}' has a larger max length ({src_max}) than target ({tgt_max}), "
                f"but no rows currently exceed the target limit. Monitor for future truncation risk."
            ),
            details=details,
        ))
    else:
        results.append(TestResult(
            name=check_name,
            status=CheckStatus.PASS,
            message=(
                f"No truncation detected for column '{column}' in '{name}'. "
                f"src_max={src_max}, tgt_max={tgt_max}"
                + (f", declared_limit={max_length}" if max_length else "")
                + "."
            ),
            details=details,
        ))

    return results


def check_whitespace_corruption(
    src_df: pd.DataFrame,
    tgt_df: pd.DataFrame,
    column: str,
    name: str,
) -> List[TestResult]:
    """Check for whitespace corruption or normalisation by comparing strip() behavior."""
    results: List[TestResult] = []
    check_name = f"Whitespace Check: {name} - {column}"

    if column not in src_df.columns or column not in tgt_df.columns:
        return [TestResult(name=check_name, status=CheckStatus.FAIL, message=f"Column '{column}' missing.")]

    src_vals = src_df[column].dropna().astype(str)
    tgt_vals = tgt_df[column].dropna().astype(str)

    if src_vals.empty:
        return [TestResult(name=check_name, status=CheckStatus.WARN, message=f"Column '{column}' empty.")]

    src_unstripped_count = (src_vals != src_vals.str.strip()).sum()
    tgt_unstripped_count = (tgt_vals != tgt_vals.str.strip()).sum()

    src_unstripped_pct = (src_unstripped_count / len(src_vals)) * 100
    tgt_unstripped_pct = (tgt_unstripped_count / len(tgt_vals)) * 100 if not tgt_vals.empty else 0

    details = {
        "src_unstripped_count": int(src_unstripped_count),
        "tgt_unstripped_count": int(tgt_unstripped_count),
        "src_unstripped_pct": round(src_unstripped_pct, 2),
        "tgt_unstripped_pct": round(tgt_unstripped_pct, 2),
    }

    if src_unstripped_count > 0 and tgt_unstripped_count == 0:
        results.append(TestResult(
            name=check_name, status=CheckStatus.WARN,
            message=f"Whitespace normalization detected in '{column}'. Source had {src_unstripped_count} unstripped rows ({src_unstripped_pct:.1f}%), Target has 0.",
            details=details
        ))
    elif tgt_unstripped_count > src_unstripped_count:
        results.append(TestResult(
            name=check_name, status=CheckStatus.FAIL,
            message=f"Whitespace corruption detected in '{column}'. Target has {tgt_unstripped_count} unstripped rows ({tgt_unstripped_pct:.1f}%), increasing from Source ({src_unstripped_count}).",
            details=details
        ))
    else:
        results.append(TestResult(
            name=check_name, status=CheckStatus.PASS,
            message=f"Whitespace handled correctly for '{column}'.",
            details=details
        ))

    return results


def check_encoding_corruption(
    src_df: pd.DataFrame,
    tgt_df: pd.DataFrame,
    column: str,
    name: str,
) -> List[TestResult]:
    """Scan strings for common encoding failure signatures (mojibake/replacement chars)."""
    results: List[TestResult] = []
    check_name = f"Encoding Check: {name} - {column}"

    if column not in src_df.columns or column not in tgt_df.columns:
        return [TestResult(name=check_name, status=CheckStatus.FAIL, message=f"Column '{column}' missing.")]

    src_vals = src_df[column].dropna().astype(str)
    tgt_vals = tgt_df[column].dropna().astype(str)

    if src_vals.empty:
        return [TestResult(name=check_name, status=CheckStatus.WARN, message=f"Column '{column}' empty.")]

    # Simple regex for unicode replacement character '' or common ISO-8859-1 mojibake prefix 'Ã'
    mojibake_pattern = r"\ufffd|Ã[-ÿ]"

    src_corrupt_count = src_vals.str.contains(mojibake_pattern, regex=True).sum()
    tgt_corrupt_count = tgt_vals.str.contains(mojibake_pattern, regex=True).sum()

    details = {
        "src_corrupt_count": int(src_corrupt_count),
        "tgt_corrupt_count": int(tgt_corrupt_count)
    }

    if tgt_corrupt_count > src_corrupt_count:
        results.append(TestResult(
            name=check_name, status=CheckStatus.FAIL,
            message=f"Encoding corruption (mojibake) detected in '{column}'. Target has {tgt_corrupt_count} corrupted rows, up from {src_corrupt_count} in source.",
            details=details
        ))
    elif src_corrupt_count > 0 and tgt_corrupt_count == 0:
        results.append(TestResult(
            name=check_name, status=CheckStatus.WARN,
            message=f"Encoding issues resolved in '{column}'. Target fixed {src_corrupt_count} previously corrupted rows.",
            details=details
        ))
    else:
        results.append(TestResult(
            name=check_name, status=CheckStatus.PASS,
            message=f"No new encoding corruption detected for '{column}'.",
            details=details
        ))

    return results
