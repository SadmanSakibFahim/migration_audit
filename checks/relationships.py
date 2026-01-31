# This check verifies that all foreign key values in the child table
# have corresponding primary key values in the parent table.

import pandas as pd
from core.result import TestResult
from core.enums import CheckStatus

def check_links(child_df: pd.DataFrame, parent_df: pd.DataFrame, fk_col: str, pk_col: str, name: str) -> TestResult:
    # Ensure columns exist before check
    if fk_col not in child_df.columns:
        return TestResult(
            name=f"Foreign Key check (Missing FK): {name}",
            status=CheckStatus.FAIL,
            message=f"Foreign key column '{fk_col}' not found in child table '{name}'."
        )
    if pk_col not in parent_df.columns:
         return TestResult(
            name=f"Foreign Key check (Missing PK): {name}",
            status=CheckStatus.FAIL,
            message=f"Primary key column '{pk_col}' not found in parent table."
        )

    null_parents = child_df[child_df[fk_col].isnull()]
    orphans = child_df[~child_df[fk_col].isin(parent_df[pk_col])]
    true_orphans = orphans[orphans[fk_col].notnull()]
                       
    if len(true_orphans) == 0 and len(null_parents) == 0:
        return TestResult(
            name=f"Foreign Key Check: {name}",
            status=CheckStatus.PASS,
            message=f"All foreign key values in '{fk_col}' of child table '{name}' have matching primary keys in parent table."
        )
    else:
        return TestResult(
            name=f"Foreign Key Check: {name}",
            status=CheckStatus.FAIL,
            message=f"Foreign key check failed for table '{name}'. Found {len(true_orphans)} orphaned foreign keys and {len(null_parents)} null foreign keys in column '{fk_col}'.",
            details={
                "orphaned_count": len(true_orphans),
                "null_count": len(null_parents)
            }
        )
