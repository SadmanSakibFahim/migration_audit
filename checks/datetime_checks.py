# checks/datetime_checks.py

from typing import List, Optional

import pandas as pd

from core.audit.enums import CheckStatus
from core.audit.result import TestResult

# DST-boundary offset signatures (in minutes) — multiples of 30min up to 14h
_COMMON_TZ_OFFSETS_MINUTES = {30, 60, 90, 120, 150, 180, 210, 240, 270, 300,
                               330, 345, 360, 390, 420, 450, 480, 510, 525,
                               540, 570, 600, 630, 660, 720, 780, 840}


def check_timezone_consistency(
    src_df: pd.DataFrame,
    tgt_df: pd.DataFrame,
    column: str,
    name: str,
    expected_tz: Optional[str] = None,
    pk_column: Optional[str] = None,
) -> List[TestResult]:
    """
    Detect timezone / DST inconsistencies in datetime columns.

    Three sub-checks:
    1. Parse failures — values that can't be parsed as datetime in either side.
    2. Timezone-awareness mismatch — one side is tz-aware, the other is naïve.
    3. Systematic offset — when rows can be joined on PK, detects consistent
       hour-boundary deltas (DST/TZ drift signatures).

    Args:
        src_df: Source DataFrame.
        tgt_df: Target DataFrame.
        column: The datetime column name.
        name: Table name (for result labeling).
        expected_tz: Optional expected timezone string (e.g. "UTC", "US/Eastern").
                     If provided, flags values that are NOT in this timezone.
        pk_column: Optional primary key column to use for row-level delta analysis.

    Returns:
        List of TestResult objects.
    """
    results: List[TestResult] = []
    base_name = f"Datetime/TZ Check: {name} - {column}"

    # Guard: column existence
    if column not in src_df.columns:
        results.append(TestResult(
            name=base_name,
            status=CheckStatus.FAIL,
            message=f"Column '{column}' not found in source table '{name}'.",
        ))
        return results

    if column not in tgt_df.columns:
        results.append(TestResult(
            name=base_name,
            status=CheckStatus.FAIL,
            message=f"Column '{column}' not found in target table '{name}'.",
        ))
        return results

    src_raw = src_df[column]
    tgt_raw = tgt_df[column]

    # --- Sub-check 1: Parse failures ---
    src_parsed = pd.to_datetime(src_raw, errors="coerce", utc=False)
    tgt_parsed = pd.to_datetime(tgt_raw, errors="coerce", utc=False)

    src_parse_failures = int(src_raw.notna().sum() - src_parsed.notna().sum())
    tgt_parse_failures = int(tgt_raw.notna().sum() - tgt_parsed.notna().sum())

    if src_parse_failures > 0 or tgt_parse_failures > 0:
        src_sample = src_raw[src_raw.notna() & src_parsed.isna()].head(3).tolist() if src_parse_failures > 0 else []
        tgt_sample = tgt_raw[tgt_raw.notna() & tgt_parsed.isna()].head(3).tolist() if tgt_parse_failures > 0 else []
        results.append(TestResult(
            name=f"{base_name} [Parse Failures]",
            status=CheckStatus.FAIL,
            message=(
                f"Unparseable datetime values in column '{column}' of '{name}': "
                f"source={src_parse_failures} failures, target={tgt_parse_failures} failures."
            ),
            details={
                "src_parse_failures": src_parse_failures,
                "tgt_parse_failures": tgt_parse_failures,
                "src_sample_bad_values": [str(v) for v in src_sample],
                "tgt_sample_bad_values": [str(v) for v in tgt_sample],
            },
        ))

    # Drop parse failures for subsequent checks
    src_valid = src_parsed.dropna()
    tgt_valid = tgt_parsed.dropna()

    if src_valid.empty or tgt_valid.empty:
        results.append(TestResult(
            name=base_name,
            status=CheckStatus.WARN,
            message=f"Not enough parseable datetime values in '{column}' for '{name}' to run TZ analysis.",
        ))
        return results

    # --- Sub-check 2: Timezone-awareness mismatch ---
    src_tz_aware = src_valid.dt.tz is not None
    tgt_tz_aware = tgt_valid.dt.tz is not None

    if src_tz_aware != tgt_tz_aware:
        results.append(TestResult(
            name=f"{base_name} [TZ Awareness Mismatch]",
            status=CheckStatus.FAIL,
            message=(
                f"Timezone awareness mismatch in column '{column}' of '{name}': "
                f"source is {'tz-aware (' + str(src_valid.dt.tz) + ')' if src_tz_aware else 'tz-naive'}, "
                f"target is {'tz-aware (' + str(tgt_valid.dt.tz) + ')' if tgt_tz_aware else 'tz-naive'}. "
                f"This is a classic DST chaos source."
            ),
            details={
                "src_tz_aware": src_tz_aware,
                "src_tz": str(src_valid.dt.tz) if src_tz_aware else None,
                "tgt_tz_aware": tgt_tz_aware,
                "tgt_tz": str(tgt_valid.dt.tz) if tgt_tz_aware else None,
            },
        ))
    else:
        # Both are consistent — check expected_tz if specified
        if expected_tz:
            try:
                src_tz_str = str(src_valid.dt.tz) if src_tz_aware else "naive"
                tgt_tz_str = str(tgt_valid.dt.tz) if tgt_tz_aware else "naive"
                if src_tz_str != expected_tz or tgt_tz_str != expected_tz:
                    results.append(TestResult(
                        name=f"{base_name} [Expected TZ]",
                        status=CheckStatus.WARN,
                        message=(
                            f"Column '{column}' in '{name}' is not in expected timezone '{expected_tz}'. "
                            f"Source TZ: '{src_tz_str}', Target TZ: '{tgt_tz_str}'."
                        ),
                        details={
                            "expected_tz": expected_tz,
                            "src_tz": src_tz_str,
                            "tgt_tz": tgt_tz_str,
                        },
                    ))
                else:
                    results.append(TestResult(
                        name=f"{base_name} [TZ Awareness]",
                        status=CheckStatus.PASS,
                        message=(
                            f"Column '{column}' in '{name}' is consistently in '{expected_tz}' on both sides."
                        ),
                    ))
            except Exception:
                pass
        else:
            results.append(TestResult(
                name=f"{base_name} [TZ Awareness]",
                status=CheckStatus.PASS,
                message=(
                    f"Timezone awareness is consistent for column '{column}' in '{name}' "
                    f"({'tz-aware: ' + str(src_valid.dt.tz) if src_tz_aware else 'both tz-naive'})."
                ),
            ))

    # --- Sub-check 3: Systematic offset (row-level delta via PK join) ---
    if pk_column and pk_column in src_df.columns and pk_column in tgt_df.columns:
        try:
            src_subset = src_df[[pk_column, column]].copy()
            tgt_subset = tgt_df[[pk_column, column]].copy()
            src_subset.columns = [pk_column, "src_ts"]
            tgt_subset.columns = [pk_column, "tgt_ts"]

            merged = pd.merge(src_subset, tgt_subset, on=pk_column, how="inner")
            if not merged.empty:
                src_ts = pd.to_datetime(merged["src_ts"], errors="coerce", utc=True)
                tgt_ts = pd.to_datetime(merged["tgt_ts"], errors="coerce", utc=True)

                # Compute delta in minutes
                valid_mask = src_ts.notna() & tgt_ts.notna()
                if valid_mask.sum() > 0:
                    deltas_minutes = (
                        (tgt_ts[valid_mask] - src_ts[valid_mask])
                        .dt.total_seconds()
                        .div(60)
                        .round()
                    )
                    median_delta = float(deltas_minutes.median())
                    abs_median = abs(median_delta)
                    std_delta = float(deltas_minutes.std())

                    # Systematic offset = median is a known TZ boundary AND std is small
                    is_systematic = (
                        abs_median in _COMMON_TZ_OFFSETS_MINUTES
                        and std_delta < 5
                    )

                    if is_systematic:
                        results.append(TestResult(
                            name=f"{base_name} [Systematic TZ Offset]",
                            status=CheckStatus.FAIL,
                            message=(
                                f"SYSTEMATIC TIMEZONE OFFSET DETECTED in column '{column}' of '{name}': "
                                f"median delta = {median_delta:+.0f} minutes ({median_delta/60:+.2f} hours). "
                                f"This is a classic DST/timezone migration bug. "
                                f"Std dev: {std_delta:.2f} min (consistent across {valid_mask.sum()} rows)."
                            ),
                            details={
                                "median_delta_minutes": median_delta,
                                "median_delta_hours": round(median_delta / 60, 2),
                                "std_delta_minutes": round(std_delta, 2),
                                "rows_analysed": int(valid_mask.sum()),
                            },
                        ))
                    elif abs_median > 0:
                        results.append(TestResult(
                            name=f"{base_name} [Timestamp Delta]",
                            status=CheckStatus.WARN,
                            message=(
                                f"Non-zero median timestamp delta in column '{column}' of '{name}': "
                                f"{median_delta:+.0f} minutes. May indicate timezone conversion. "
                                f"Std dev: {std_delta:.2f} min."
                            ),
                            details={
                                "median_delta_minutes": median_delta,
                                "std_delta_minutes": round(std_delta, 2),
                                "rows_analysed": int(valid_mask.sum()),
                            },
                        ))
                    else:
                        results.append(TestResult(
                            name=f"{base_name} [Timestamp Delta]",
                            status=CheckStatus.PASS,
                            message=(
                                f"No systematic timezone offset detected in '{column}' of '{name}'. "
                                f"Median delta = 0 min across {valid_mask.sum()} matched rows."
                            ),
                            details={
                                "median_delta_minutes": median_delta,
                                "rows_analysed": int(valid_mask.sum()),
                            },
                        ))
        except Exception as e:
            results.append(TestResult(
                name=f"{base_name} [Timestamp Delta ERROR]",
                status=CheckStatus.ERROR,
                message=f"Could not compute row-level timestamp delta for '{column}': {e}",
            ))

    return results
