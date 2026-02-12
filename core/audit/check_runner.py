import pandas as pd
from core.audit.logger import get_logger
from core.audit.result import TestResult
from core.audit.enums import CheckStatus

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

    def _safe_run(self, category: str, fn, *args, **kwargs):
        """Run a check function with graceful error handling."""
        try:
            result = fn(*args, **kwargs)
            return self._normalize_result(result)
        except Exception as e:
            logger.error(
                f"Check '{category}' failed for table '{self.table_name}': {e}",
                exc_info=True,
            )
            return [TestResult(
                name=f"{category} (ERROR): {self.table_name}",
                status=CheckStatus.ERROR,
                message=f"Check crashed: {type(e).__name__}: {e}",
                details={"exception": str(e), "category": category},
            )]

    def _validate_dataframes(self) -> bool:
        """Validate source and target DataFrames before running checks.
        
        Returns True if DataFrames are valid enough to proceed.
        Appends WARN results for edge cases but still returns True.
        Returns False only if DataFrames are fundamentally broken.
        """
        # Check for None DataFrames
        if self.src_df is None or self.tgt_df is None:
            which = []
            if self.src_df is None:
                which.append("source")
            if self.tgt_df is None:
                which.append("target")
            self.results.append(TestResult(
                name=f"DataFrame Validation: {self.table_name}",
                status=CheckStatus.FAIL,
                message=f"Cannot run checks — {' and '.join(which)} DataFrame is None for table '{self.table_name}'.",
            ))
            return False

        # Check for non-DataFrame types
        if not isinstance(self.src_df, pd.DataFrame) or not isinstance(self.tgt_df, pd.DataFrame):
            self.results.append(TestResult(
                name=f"DataFrame Validation: {self.table_name}",
                status=CheckStatus.FAIL,
                message=f"Invalid data type — expected DataFrame, got source={type(self.src_df).__name__}, target={type(self.tgt_df).__name__}.",
            ))
            return False

        # Warn on empty DataFrames but allow checks to proceed
        if self.src_df.empty and self.tgt_df.empty:
            logger.warning(f"Both source and target DataFrames are empty for '{self.table_name}'")
        elif self.src_df.empty:
            logger.warning(f"Source DataFrame is empty for '{self.table_name}' (target has {len(self.tgt_df)} rows)")
        elif self.tgt_df.empty:
            logger.warning(f"Target DataFrame is empty for '{self.table_name}' (source has {len(self.src_df)} rows)")

        return True

    def execute_all(self):
        from core.audit.check_registry import CHECK_REGISTRY

        # --- Validate DataFrames before running any checks ---
        if not self._validate_dataframes():
            logger.error(f"Aborting checks for '{self.table_name}' due to invalid DataFrames")
            return self.results

        # -----------------------------
        # Volume checks
        # -----------------------------
        for fn in CHECK_REGISTRY.get("volume", []):
            self.results.extend(self._safe_run(
                "Volume Check", fn,
                self.table_name,
                self.src_df,
                self.tgt_df,
                self.volume_tolerance,
            ))

        # -----------------------------
        # Identity Checks (PK Overlap)
        # -----------------------------
        pk = getattr(self.meta, "primary_key", None)
        if pk and pk in self.src_df.columns and pk in self.tgt_df.columns:
            try:
                src_ids = set(self.src_df[pk].dropna().unique())
                tgt_ids = set(self.tgt_df[pk].dropna().unique())
                
                overlap = src_ids.intersection(tgt_ids)
                overlap_pct = (len(overlap) / len(src_ids) * 100) if src_ids else 0
                
                # We expect high overlap in a migration
                status = CheckStatus.PASS if overlap_pct >= 95 else (CheckStatus.WARN if overlap_pct > 0 else CheckStatus.FAIL)
                
                message = f"Identity Overlap: {overlap_pct:.2f}% of source IDs found in target."
                if overlap_pct == 0:
                    message = "CRITICAL: 0% overlap detected! Source and Target share NO Primary Keys."

                # Note NULL PKs as a separate warning
                src_null_pks = self.src_df[pk].isnull().sum()
                tgt_null_pks = self.tgt_df[pk].isnull().sum()
                if src_null_pks > 0 or tgt_null_pks > 0:
                    message += f" (NULL PK values: source={src_null_pks}, target={tgt_null_pks})"
                    
                self.results.append(TestResult(
                    name=f"Identity Check: {self.table_name}",
                    status=status,
                    message=message,
                    details={
                        "overlap_pct": overlap_pct,
                        "common_rows": len(overlap),
                        "src_null_pks": int(src_null_pks),
                        "tgt_null_pks": int(tgt_null_pks),
                    }
                ))
            except Exception as e:
                logger.error(f"Identity check failed for '{self.table_name}': {e}", exc_info=True)
                self.results.append(TestResult(
                    name=f"Identity Check (ERROR): {self.table_name}",
                    status=CheckStatus.ERROR,
                    message=f"Identity check crashed: {type(e).__name__}: {e}",
                ))

        # -----------------------------
        # Aggregate checks
        # -----------------------------
        for col in getattr(self.meta, "aggregates", []):
            try:
                # Handle column mapping for complex mappings
                src_col = col
                tgt_col = col
                if hasattr(self.meta, 'aggregate_column_mapping') and self.meta.aggregate_column_mapping:
                    if col in self.meta.aggregate_column_mapping.values():
                        src_col = next(k for k, v in self.meta.aggregate_column_mapping.items() if v == col)
                    elif col in self.meta.aggregate_column_mapping:
                        src_col = self.meta.aggregate_column_mapping[col]
                
                # Check if columns exist in dataframes
                if src_col not in self.src_df.columns:
                    self.results.append(TestResult(
                        name=f"Aggregate check (Source Column Missing): {src_col}",
                        status=CheckStatus.FAIL,
                        message=f"Source column '{src_col}' not found in table '{self.table_name}'. Available columns: {list(self.src_df.columns[:10])}{'...' if len(self.src_df.columns) > 10 else ''}",
                    ))
                    continue
                
                if tgt_col not in self.tgt_df.columns:
                    self.results.append(TestResult(
                        name=f"Aggregate Check: {self.table_name} - {col}",
                        status=CheckStatus.WARN,
                        message=f"Target column '{tgt_col}' not found in table '{self.table_name}'. Available columns: {list(self.tgt_df.columns[:10])}{'...' if len(self.tgt_df.columns) > 10 else ''}",
                    ))
                    continue

                # Data Quality: Check for non-numeric junk in a supposedly numeric column
                tgt_vals_coerced = pd.to_numeric(self.tgt_df[tgt_col], errors='coerce')
                junk_mask = self.tgt_df[tgt_col].notna() & tgt_vals_coerced.isna()
                junk_count = int(junk_mask.sum())
                
                if junk_count > 0:
                    sample_values = self.tgt_df.loc[junk_mask, tgt_col].head(5).tolist()
                    self.results.append(TestResult(
                        name=f"Data Quality: {self.table_name}.{tgt_col}",
                        status=CheckStatus.FAIL,
                        message=f"Found {junk_count} non-numeric junk values in target column '{tgt_col}'. Samples: {sample_values}",
                        details={"junk_rows": junk_count, "sample_values": sample_values}
                    ))

                for fn in CHECK_REGISTRY.get("aggregates", []):
                    results = self._safe_run(
                        f"Aggregate Check ({col})", fn,
                        self.src_df,
                        self.tgt_df,
                        src_col,
                        self.table_name,
                        self.aggregate_tolerance,
                    )
                    # Update result to show target column name if different
                    if src_col != tgt_col:
                        for r in results:
                            if hasattr(r, 'name'):
                                r.name = r.name.replace(src_col, f"{src_col}->{tgt_col}")
                    self.results.extend(results)

            except Exception as e:
                logger.error(f"Aggregate check for column '{col}' on '{self.table_name}' failed: {e}", exc_info=True)
                self.results.append(TestResult(
                    name=f"Aggregate Check (ERROR): {self.table_name}.{col}",
                    status=CheckStatus.ERROR,
                    message=f"Aggregate check crashed for column '{col}': {type(e).__name__}: {e}",
                ))

        # -----------------------------
        # Mapping checks
        # -----------------------------
        for mapping in getattr(self.meta, "mappings", []):
            for fn in CHECK_REGISTRY.get("mappings", []):
                self.results.extend(self._safe_run(
                    "Mapping Check", fn,
                    self.tgt_df,
                    mapping.columns,
                    mapping.allowed_values,
                    self.table_name,
                ))

        # -----------------------------
        # Relationship checks
        # -----------------------------
        for rel in getattr(self.meta, "relationships", []):
            for fn in CHECK_REGISTRY.get("relationships", []):
                self.results.extend(self._safe_run(
                    "Relationship Check", fn,
                    self.tgt_df,          # child_df
                    self.tgt_df,          # parent_df (STUB: should load reference_table)
                    rel.child["fk_column"],
                    rel.parent["pk_column"],
                    self.table_name,
                ))

        # -----------------------------
        # Data constraint checks
        # -----------------------------
        from checks.data_constraints import check_data_constraints
        for col, constraints in getattr(self.meta, "data_constraints", {}).items():
            if isinstance(constraints, str):
                constraints = [constraints]
            self.results.extend(self._safe_run(
                f"Data Constraint Check ({col})",
                check_data_constraints,
                self.tgt_df, {col: constraints}, self.table_name,
            ))

        return self.results
