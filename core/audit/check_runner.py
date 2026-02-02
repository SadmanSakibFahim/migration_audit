import pandas as pd
from core.audit.logger import get_logger

logger = get_logger(__name__)


class CheckRunner:
    def __init__(
        self,
        table_name,
        meta,
        src_df,
        tgt_df,
        volume_tolerance=0.1,
        aggregate_tolerance=1.0,
    ):
        self.table_name = table_name
        self.meta = meta
        self.src_df = src_df
        self.tgt_df = tgt_df
        self.volume_tolerance = volume_tolerance
        self.aggregate_tolerance = aggregate_tolerance
        self.results = []

    def _normalize_result(self, result):
        if result is None:
            return []
        if isinstance(result, list):
            return result
        return [result]

    def execute_all(self):
        from core.audit.check_registry import CHECK_REGISTRY
        # -----------------------------
        # Volume checks
        # -----------------------------
        for fn in CHECK_REGISTRY.get("volume", []):
            result = fn(
                self.table_name,     # First arg is name
                self.src_df,
                self.tgt_df,
                self.volume_tolerance,
            )
            self.results.extend(self._normalize_result(result))

        # -----------------------------
        # Identity Checks (PK Overlap)
        # -----------------------------
        pk = getattr(self.meta, "primary_key", None)
        if pk and pk in self.src_df.columns and pk in self.tgt_df.columns:
            from core.audit.result import TestResult
            from core.audit.enums import CheckStatus
            
            src_ids = set(self.src_df[pk].unique())
            tgt_ids = set(self.tgt_df[pk].unique())
            
            overlap = src_ids.intersection(tgt_ids)
            overlap_pct = (len(overlap) / len(src_ids) * 100) if src_ids else 0
            
            # We expect high overlap in a migration
            status = CheckStatus.PASS if overlap_pct >= 95 else (CheckStatus.WARN if overlap_pct > 0 else CheckStatus.FAIL)
            
            message = f"Identity Overlap: {overlap_pct:.2f}% of source IDs found in target."
            if overlap_pct == 0:
                message = "CRITICAL: 0% overlap detected! Source and Target share NO Primary Keys."
                
            self.results.append(TestResult(
                name=f"Identity Check: {self.table_name}",
                status=status,
                message=message,
                details={"overlap_pct": overlap_pct, "common_rows": len(overlap)}
            ))

        # -----------------------------
        # Aggregate checks
        # -----------------------------
        for col in getattr(self.meta, "aggregates", []):
            # Handle column mapping for complex mappings
            src_col = col
            tgt_col = col
            if hasattr(self.meta, 'aggregate_column_mapping') and self.meta.aggregate_column_mapping:
                # If target column is mapped, use the source column name
                if col in self.meta.aggregate_column_mapping.values():
                    # Find the source column name
                    src_col = next(k for k, v in self.meta.aggregate_column_mapping.items() if v == col)
                elif col in self.meta.aggregate_column_mapping:
                    # Target column is the key, source is the value
                    src_col = self.meta.aggregate_column_mapping[col]
            
            # Check if columns exist in dataframes
            if src_col not in self.src_df.columns:
                from core.audit.result import TestResult
                from core.audit.enums import CheckStatus
                self.results.append(TestResult(
                    name=f"Aggregate check (Source Column Missing): {src_col}",
                    status=CheckStatus.FAIL,
                    message=f"Source column '{src_col}' not found for aggregate check."
                ))
                continue
            
            if tgt_col not in self.tgt_df.columns:
                from core.audit.result import TestResult
                from core.audit.enums import CheckStatus
                self.results.append(TestResult(
                    name=f"Aggregate Check: {self.table_name} - {col}",
                    status=CheckStatus.WARN,
                    message=f"Target column '{tgt_col}' not found in target data for aggregate check."
                ))
                continue

            # Data Quality: Check for non-numeric junk in a supposedly numeric column
            tgt_vals_coerced = pd.to_numeric(self.tgt_df[tgt_col], errors='coerce')
            junk_mask = self.tgt_df[tgt_col].notna() & tgt_vals_coerced.isna()
            junk_count = junk_mask.sum()
            
            if junk_count > 0:
                from core.audit.result import TestResult
                from core.audit.enums import CheckStatus
                self.results.append(TestResult(
                    name=f"Data Quality: {self.table_name}.{tgt_col}",
                    status=CheckStatus.FAIL,
                    message=f"Found {junk_count} non-numeric junk values (e.g., '{self.tgt_df.loc[junk_mask, tgt_col].iloc[0]}') in target column '{tgt_col}'.",
                    details={"junk_rows": int(junk_count)}
                ))

            
            for fn in CHECK_REGISTRY.get("aggregates", []):
                result = fn(
                    self.src_df,
                    self.tgt_df,
                    src_col,  # Use source column name
                    self.table_name,
                    self.aggregate_tolerance,
                )
                # Update result to show target column name if different
                if src_col != tgt_col and result:
                    if isinstance(result, list):
                        for r in result:
                            if hasattr(r, 'name'):
                                r.name = r.name.replace(src_col, f"{src_col}->{tgt_col}")
                    elif hasattr(result, 'name'):
                        result.name = result.name.replace(src_col, f"{src_col}->{tgt_col}")
                self.results.extend(self._normalize_result(result))

        # -----------------------------
        # Mapping checks
        # -----------------------------
        for mapping in getattr(self.meta, "mappings", []):
            for fn in CHECK_REGISTRY.get("mappings", []):
                result = fn(
                    self.tgt_df,
                    mapping.columns,
                    mapping.allowed_values,
                    self.table_name,
                )
                self.results.extend(self._normalize_result(result))

        # -----------------------------
        # Relationship checks
        # -----------------------------
        for rel in getattr(self.meta, "relationships", []):
            for fn in CHECK_REGISTRY.get("relationships", []):
                # NOTE: check_links needs the parent_df. For now we use tgt_df 
                # but in a real enterprise audit we'd load the reference table.
                result = fn(
                    self.tgt_df,          # child_df
                    self.tgt_df,          # parent_df (STUB: should load reference_table)
                    rel.child["fk_column"],           # fk_col
                    rel.parent["pk_column"], # pk_col
                    self.table_name,      # name
                )
                self.results.extend(self._normalize_result(result))

        # -----------------------------
        # Data constraint checks
        # -----------------------------
        from checks.data_constraints import check_data_constraints
        for col, constraints in getattr(self.meta, "data_constraints", {}).items():
            if isinstance(constraints, str):
                constraints = [constraints]
            result = check_data_constraints(
                self.tgt_df, {col: constraints}, self.table_name
            )
            self.results.extend(self._normalize_result(result))

        return self.results
