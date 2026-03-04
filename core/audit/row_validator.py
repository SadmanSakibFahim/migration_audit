"""
Row validation module for identifying and filtering invalid rows.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

import pandas as pd

from core.audit.config_models import TableConfig
from core.audit.logger import get_logger

logger = get_logger(__name__)

# Global log of all invalid rows across the audit
_invalid_rows_log: List[Dict[str, Any]] = []


class InvalidRowInfo:
    """Information about an invalid row."""

    def __init__(self, row_index: int, row_data: pd.Series, reasons: List[str]):
        self.row_index = row_index
        self.row_data = row_data
        self.reasons = reasons

    def to_dict(self) -> Dict[Any, Any]:
        """Convert to dictionary for CSV export."""
        result = self.row_data.to_dict()
        result["_row_index"] = self.row_index
        result["_validation_errors"] = "; ".join(self.reasons)
        return result


def validate_rows(
    df: pd.DataFrame, table_config: TableConfig, table_name: str, is_source: bool = True
) -> Tuple[pd.DataFrame, List[InvalidRowInfo]]:
    """
    Validate rows in a DataFrame based on table configuration.

    Args:
        df: DataFrame to validate
        table_config: Table configuration with constraints
        table_name: Name of the table
        is_source: Whether this is source data (True) or target data (False)

    Returns:
        Tuple of (valid_dataframe, list_of_invalid_rows)
    """
    invalid_rows: List[InvalidRowInfo] = []
    valid_indices = []

    # Validate each row
    for idx, row in df.iterrows():
        reasons = []

        # Check data constraints
        if hasattr(table_config, "data_constraints") and table_config.data_constraints:
            for col, constraints in table_config.data_constraints.items():
                if col not in df.columns:
                    continue

                # Handle both list and single string constraints
                constraint_list = (
                    constraints if isinstance(constraints, list) else [constraints]
                )

                if "not_null" in constraint_list:
                    if pd.isna(row[col]) or row[col] == "":
                        reasons.append(f"Column '{col}' is null (not_null constraint)")

                if "date" in constraint_list:
                    if not pd.isna(row[col]) and row[col] != "":
                        try:
                            pd.to_datetime(row[col], errors="raise")
                        except (ValueError, TypeError):
                            reasons.append(
                                f"Column '{col}' has invalid date value: {row[col]}"
                            )

        # #region agent log
        if reasons:
            import json

            try:
                with open(".cursor\\debug.log", "a", encoding="utf-8") as f:
                    f.write(
                        json.dumps(
                            {
                                "sessionId": "debug-session",
                                "runId": "run1",
                                "hypothesisId": "D",
                                "location": "row_validator.py:55",
                                "message": "Row validation failure",
                                "data": {
                                    "table_name": table_name,
                                    "row_index": int(str(idx)),
                                    "reasons": reasons,
                                    "sample_values": {
                                        col: str(row[col])[:50]
                                        for col in df.columns[:5]
                                    },
                                },
                                "timestamp": int(__import__("time").time() * 1000),
                            }
                        )
                        + "\n"
                    )
            except Exception:
                pass
        # #endregion

        # Check mapping constraints (only for target data)
        if (
            not is_source
            and hasattr(table_config, "mappings")
            and table_config.mappings
        ):
            for mapping in table_config.mappings:
                for col in mapping.columns:
                    if col in df.columns:
                        if (
                            not pd.isna(row[col])
                            and row[col] not in mapping.allowed_values
                        ):
                            reasons.append(
                                f"Column '{col}' has invalid value '{row[col]}' "
                                f"(allowed: {', '.join(mapping.allowed_values)})"
                            )

        # Check primary key uniqueness (for target data)
        if not is_source and hasattr(table_config, "primary_key"):
            pk_col = table_config.primary_key
            if pk_col in df.columns:
                # Check for duplicate primary keys (only flag if not first occurrence)
                if not pd.isna(row[pk_col]):
                    duplicates = df[df[pk_col] == row[pk_col]]
                    if len(duplicates) > 1 and idx != duplicates.index[0]:
                        reasons.append(
                            f"Duplicate primary key '{row[pk_col]}' in column '{pk_col}'"
                        )

        if reasons:
            invalid_rows.append(InvalidRowInfo(int(str(idx)), row, reasons))
        else:
            valid_indices.append(idx)

    # Filter to valid rows only
    valid_df = df.loc[valid_indices].copy()

    logger.info(
        f"{table_name} ({'source' if is_source else 'target'}): "
        f"Found {len(invalid_rows)} invalid rows out of {len(df)} total rows"
    )

    return valid_df, invalid_rows


def export_invalid_rows(
    invalid_rows: List[InvalidRowInfo],
    file_path: str,
    table_name: str,
    is_source: bool = True,
) -> Optional[str]:
    """
    Export invalid rows to a CSV file and log them.

    Args:
        invalid_rows: List of InvalidRowInfo objects
        file_path: Original file path
        table_name: Name of the table
        is_source: Whether this is source data

    Returns:
        Path to the exported CSV file
    """
    if not invalid_rows:
        return None

    # Determine the directory of the original file
    original_path = Path(file_path)
    data_dir = original_path.parent

    # Create invalid_data subfolder
    invalid_dir = data_dir / "invalid_data"
    invalid_dir.mkdir(exist_ok=True)

    # Generate output filename
    file_type = "source" if is_source else "target"
    base_name = original_path.stem
    output_file = invalid_dir / f"{base_name}_invalid_{file_type}.csv"

    # Convert to DataFrame for export
    invalid_data = [row_info.to_dict() for row_info in invalid_rows]
    invalid_df = pd.DataFrame(invalid_data)

    # Export to CSV
    invalid_df.to_csv(output_file, index=False)

    # Log to global log
    for row_info in invalid_rows:
        _invalid_rows_log.append(
            {
                "table_name": table_name,
                "file_path": str(file_path),
                "file_type": file_type,
                "row_index": row_info.row_index,
                "reasons": "; ".join(row_info.reasons),
                "exported_to": str(output_file),
            }
        )

    logger.info(
        f"Exported {len(invalid_rows)} invalid rows from '{table_name}' "
        f"({file_type}) to: {output_file}"
    )

    return str(output_file)


def create_invalid_rows_summary_log(output_dir: str) -> Optional[str]:
    """
    Create a summary log file of all invalid rows across the entire audit.

    Args:
        output_dir: Directory where the summary log should be created

    Returns:
        Path to the summary log file
    """
    if not _invalid_rows_log:
        return None

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = output_path / f"invalid_rows_summary_{timestamp}.log"

    with open(log_file, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("INVALID ROWS SUMMARY LOG\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total invalid rows: {len(_invalid_rows_log)}\n")
        f.write("=" * 80 + "\n\n")

        # Group by table
        from collections import defaultdict

        by_table = defaultdict(list)
        for entry in _invalid_rows_log:
            by_table[entry["table_name"]].append(entry)

        for table_name, entries in by_table.items():
            f.write(f"\nTable: {table_name}\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total invalid rows: {len(entries)}\n\n")

            for entry in entries:
                f.write(f"  File: {entry['file_path']} ({entry['file_type']})\n")
                f.write(f"  Row Index: {entry['row_index']}\n")
                f.write(f"  Reasons: {entry['reasons']}\n")
                f.write(f"  Exported to: {entry['exported_to']}\n")
                f.write("\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("END OF SUMMARY\n")
        f.write("=" * 80 + "\n")

    logger.info(f"Created invalid rows summary log: {log_file}")
    return str(log_file)


def reset_invalid_rows_log() -> None:
    """Reset the global invalid rows log (useful for testing)."""
    global _invalid_rows_log
    _invalid_rows_log = []
