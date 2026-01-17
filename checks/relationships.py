# This check verifies that all foreign key values in the child table
# have corresponding primary key values in the parent table.

# This check also includes whether there are any nulls in the foreign key column.

import pandas as pd
from core.result import TestResult
from core.enums import CheckStatus

def check_links(child_df: pd.DataFrame, parent_df: pd.DataFrame, fk_col: str, pk_col: str, name: str) -> TestResult:
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
                "null_foreign_keys": null_parents.to_dict(orient="records"),
                "orphaned_foreign_keys": true_orphans.to_dict(orient="records")
            }
        )
