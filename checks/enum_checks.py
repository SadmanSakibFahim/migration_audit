# checks/enum_checks.py

from typing import Any, Dict, List, Optional

import pandas as pd

from core.audit.enums import CheckStatus
from core.audit.result import TestResult


def check_enum_equivalence(
    src_df: pd.DataFrame,
    tgt_df: pd.DataFrame,
    column: str,
    name: str,
    mapping: Optional[Dict[str, Any]] = None,
) -> List[TestResult]:
    """
    Detect enum value mismatches between source and target columns.

    Two modes:
    1. Raw set comparison (no mapping): flags any value present in source but
       absent in target or vice versa.
    2. Mapping mode: validates that every source value has a declared mapping,
       and counts rows in target that received unmapped/unexpected values.

    Args:
        src_df: Source DataFrame.
        tgt_df: Target DataFrame.
        column: The column name to check.
        name: Table name (for result labeling).
        mapping: Optional dict mapping source values → expected target values.
                 e.g. {"active": "A", "inactive": "I"}

    Returns:
        List of TestResult objects.
    """
    results: List[TestResult] = []
    check_name = f"Enum Equivalence Check: {name} - {column}"

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

    src_values = src_df[column].dropna()
    tgt_values = tgt_df[column].dropna()

    src_distinct = set(src_values.unique())
    tgt_distinct = set(tgt_values.unique())

    if mapping:
        # --- Mapping Mode ---
        # All source values that have no declared mapping
        unmapped_src_values = src_distinct - set(mapping.keys())
        # Source values whose mapping leads to a value NOT in the target
        expected_tgt_values = set(mapping.values())
        missing_in_target = expected_tgt_values - tgt_distinct
        # Values in target that were never expected from the mapping
        orphaned_tgt_values = tgt_distinct - expected_tgt_values

        # Count rows affected
        unmapped_row_count = int(src_values.isin(unmapped_src_values).sum())
        orphaned_row_count = int(tgt_values.isin(orphaned_tgt_values).sum())

        issues = []
        if unmapped_src_values:
            issues.append(
                f"{len(unmapped_src_values)} source value(s) have no declared mapping: "
                f"{sorted(str(v) for v in unmapped_src_values)} "
                f"({unmapped_row_count} rows affected)"
            )
        if missing_in_target:
            issues.append(
                f"Mapped target values not found in target column: "
                f"{sorted(str(v) for v in missing_in_target)}"
            )
        if orphaned_tgt_values:
            issues.append(
                f"{len(orphaned_tgt_values)} unexpected value(s) in target "
                f"(not in any declared mapping): "
                f"{sorted(str(v) for v in orphaned_tgt_values)} "
                f"({orphaned_row_count} rows)"
            )

        details = {
            "src_distinct_values": sorted(str(v) for v in src_distinct),
            "tgt_distinct_values": sorted(str(v) for v in tgt_distinct),
            "declared_mapping": {str(k): str(v) for k, v in mapping.items()},
            "unmapped_source_values": sorted(str(v) for v in unmapped_src_values),
            "orphaned_target_values": sorted(str(v) for v in orphaned_tgt_values),
            "unmapped_row_count": unmapped_row_count,
            "orphaned_row_count": orphaned_row_count,
        }

        if issues:
            results.append(TestResult(
                name=check_name,
                status=CheckStatus.FAIL,
                message=(
                    f"Enum mapping issues in column '{column}' of table '{name}': "
                    + "; ".join(issues)
                ),
                details=details,
            ))
        else:
            results.append(TestResult(
                name=check_name,
                status=CheckStatus.PASS,
                message=(
                    f"All enum values in '{column}' correctly mapped for table '{name}'. "
                    f"Source: {sorted(str(v) for v in src_distinct)}, "
                    f"Target: {sorted(str(v) for v in tgt_distinct)}."
                ),
                details=details,
            ))
    else:
        # --- Raw Set Comparison Mode ---
        in_src_not_tgt = src_distinct - tgt_distinct
        in_tgt_not_src = tgt_distinct - src_distinct

        # Count rows in source that have values absent from target
        orphaned_src_row_count = int(src_values.isin(in_src_not_tgt).sum()) if in_src_not_tgt else 0
        orphaned_tgt_row_count = int(tgt_values.isin(in_tgt_not_src).sum()) if in_tgt_not_src else 0

        details = {
            "src_distinct_values": sorted(str(v) for v in src_distinct),
            "tgt_distinct_values": sorted(str(v) for v in tgt_distinct),
            "in_source_not_target": sorted(str(v) for v in in_src_not_tgt),
            "in_target_not_source": sorted(str(v) for v in in_tgt_not_src),
            "src_rows_with_missing_values": orphaned_src_row_count,
            "tgt_rows_with_extra_values": orphaned_tgt_row_count,
        }

        if in_src_not_tgt or in_tgt_not_src:
            issues = []
            if in_src_not_tgt:
                issues.append(
                    f"Values in source but NOT in target: "
                    f"{sorted(str(v) for v in in_src_not_tgt)} "
                    f"({orphaned_src_row_count} rows)"
                )
            if in_tgt_not_src:
                issues.append(
                    f"Values in target but NOT in source: "
                    f"{sorted(str(v) for v in in_tgt_not_src)} "
                    f"({orphaned_tgt_row_count} rows)"
                )
            results.append(TestResult(
                name=check_name,
                status=CheckStatus.FAIL,
                message=(
                    f"Enum value set mismatch in column '{column}' of table '{name}': "
                    + "; ".join(issues)
                ),
                details=details,
            ))
        else:
            results.append(TestResult(
                name=check_name,
                status=CheckStatus.PASS,
                message=(
                    f"Enum value sets match for column '{column}' in table '{name}'. "
                    f"Distinct values: {sorted(str(v) for v in src_distinct)}."
                ),
                details=details,
            ))

    return results


def check_categorical_distribution(
    src_df: pd.DataFrame,
    tgt_df: pd.DataFrame,
    column: str,
    name: str,
    tolerance_pct: float = 0.05
) -> List[TestResult]:
    """Flag if the relative proportions of categories shift by more than tolerance_pct."""
    results: List[TestResult] = []
    check_name = f"Categorical Distribution Check: {name} - {column}"

    if column not in src_df.columns or column not in tgt_df.columns:
        return [TestResult(name=check_name, status=CheckStatus.FAIL, message=f"Column '{column}' missing.")]

    src_counts = src_df[column].dropna().value_counts(normalize=True)
    tgt_counts = tgt_df[column].dropna().value_counts(normalize=True)

    if src_counts.empty or tgt_counts.empty:
        return [TestResult(name=check_name, status=CheckStatus.WARN, message=f"Column '{column}' empty.")]

    # Align indexes and fill missing with 0 for comparison
    df_compare = pd.DataFrame({'src': src_counts, 'tgt': tgt_counts}).fillna(0)
    df_compare['diff'] = (df_compare['src'] - df_compare['tgt']).abs()

    max_shift_cat = df_compare['diff'].idxmax()
    max_shift_val = df_compare['diff'].max()

    details = {
        "max_shift_cat": str(max_shift_cat),
        "max_shift_val": round(max_shift_val, 4),
        "tolerance": tolerance_pct
    }

    if max_shift_val > tolerance_pct:
        results.append(TestResult(
            name=check_name, status=CheckStatus.WARN,
            message=f"Categorical distribution shift detected in '{column}'. Category '{max_shift_cat}' shifted by {max_shift_val*100:.1f}%, exceeding tolerance of {tolerance_pct*100:.1f}%.",
            details=details
        ))
    else:
        results.append(TestResult(
            name=check_name, status=CheckStatus.PASS,
            message=f"Categorical distribution stable for '{column}'. Max shift: {max_shift_val*100:.1f}%.",
            details=details
        ))

    return results


def check_boolean_normalization(
    src_df: pd.DataFrame,
    tgt_df: pd.DataFrame,
    column: str,
    name: str,
    true_values: List[str],
    false_values: List[str]
) -> List[TestResult]:
    """Map variants of True/False to strict booleans and check proportion preservation."""
    results: List[TestResult] = []
    check_name = f"Boolean Normalization Check: {name} - {column}"

    if column not in src_df.columns or column not in tgt_df.columns:
        return [TestResult(name=check_name, status=CheckStatus.FAIL, message=f"Column '{column}' missing.")]

    src_vals = src_df[column].dropna().astype(str).str.strip()
    tgt_vals = tgt_df[column].dropna().astype(str).str.strip()

    if src_vals.empty:
        return [TestResult(name=check_name, status=CheckStatus.WARN, message=f"Column '{column}' empty.")]

    def _normalize(s):
        if s in true_values: return True
        if s in false_values: return False
        return None

    src_mapped = src_vals.apply(_normalize).dropna()
    tgt_mapped = tgt_vals.apply(_normalize).dropna()

    src_true_pct = src_mapped.mean() if not src_mapped.empty else 0
    tgt_true_pct = tgt_mapped.mean() if not tgt_mapped.empty else 0

    diff = abs(src_true_pct - tgt_true_pct)
    
    details = {
        "src_true_pct": round(src_true_pct, 4),
        "tgt_true_pct": round(tgt_true_pct, 4),
        "diff": round(diff, 4)
    }

    if diff > 0.001:  # Allow 0.1% floating tolerance
        results.append(TestResult(
            name=check_name, status=CheckStatus.FAIL,
            message=f"Boolean ratio mismatch in '{column}'. Source True %: {src_true_pct:.2%}, Target True %: {tgt_true_pct:.2%}.",
            details=details
        ))
    else:
        results.append(TestResult(
            name=check_name, status=CheckStatus.PASS,
            message=f"Boolean ratio preserved perfectly for '{column}' ({tgt_true_pct:.2%} True).",
            details=details
        ))

    return results
