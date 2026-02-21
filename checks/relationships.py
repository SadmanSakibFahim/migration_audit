# This check verifies that all foreign key values in the child table
# have corresponding primary key values in the parent table.

import pandas as pd

from core.audit.enums import CheckStatus
from core.audit.result import TestResult


def check_links(
    child_df: pd.DataFrame,
    parent_df: pd.DataFrame,
    fk_column: str,
    pk_column: str,
    table_name: str,
) -> TestResult:
    """
    Verifies referential integrity between child and parent tables.
    """
    # Guard: None or empty DataFrames
    if child_df is None or not isinstance(child_df, pd.DataFrame):
        return TestResult(
            name=f"Foreign Key Check: {table_name}",
            status=CheckStatus.FAIL,
            message=f"Cannot run FK check — child DataFrame is None or invalid for table '{table_name}'.",
        )
    if parent_df is None or not isinstance(parent_df, pd.DataFrame):
        return TestResult(
            name=f"Foreign Key Check: {table_name}",
            status=CheckStatus.FAIL,
            message=f"Cannot run FK check — parent DataFrame is None or invalid for table '{table_name}'.",
        )
    if child_df.empty:
        return TestResult(
            name=f"Foreign Key Check: {table_name}",
            status=CheckStatus.WARN,
            message=f"Child DataFrame is empty for table '{table_name}' — FK check skipped.",
        )
    if fk_column not in child_df.columns:
        return TestResult(
            name=f"Foreign Key check (Missing FK): {table_name}",
            status=CheckStatus.FAIL,
            message=f"Foreign key column '{fk_column}' not found in child table '{table_name}'.",
        )
    if pk_column not in parent_df.columns:
        return TestResult(
            name=f"Foreign Key check (Missing PK): {table_name}",
            status=CheckStatus.FAIL,
            message=f"Primary key column '{pk_column}' not found in parent table.",
        )

    null_parents = child_df[child_df[fk_column].isnull()]
    orphans = child_df[~child_df[fk_column].isin(parent_df[pk_column])]
    true_orphans = orphans[orphans[fk_column].notnull()]

    if len(true_orphans) == 0 and len(null_parents) == 0:
        return TestResult(
            name=f"Foreign Key Check: {table_name}",
            status=CheckStatus.PASS,
            message=f"All foreign key values in '{fk_column}' of child table '{table_name}' have matching primary keys in parent table.",
        )
    else:
        return TestResult(
            name=f"Foreign Key Check: {table_name}",
            status=CheckStatus.FAIL,
            message=f"Foreign key check failed for table '{table_name}'. Found {len(true_orphans)} orphaned foreign keys and {len(null_parents)} null foreign keys in column '{fk_column}'.",
            details={
                "orphaned_count": len(true_orphans),
                "null_count": len(null_parents),
            },
        )
