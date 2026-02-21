import pandas as pd

from core.audit.enums import CheckStatus
from core.audit.logger import get_logger
from core.audit.result import TestResult

logger = get_logger(__name__)


class CheckRunner:
    def __init__(
        self,
        table_name,
        meta,
        src_df,
        tgt_df,
        config=None,
        progress_callback=None,
    ):
        self.table_name = table_name
        self.meta = meta
        self.src_df = src_df
        self.tgt_df = tgt_df
        self.config = config or {}
        self.progress_callback = progress_callback

        # Extract configuration with defaults
        self.volume_tolerance = self.config.get("volume_tolerance", 0.1)
        self.aggregate_tolerance = self.config.get("aggregate_tolerance", 1.0)
        self.identity_overlap_threshold = self.config.get(
            "identity_overlap_threshold", 95
        )

        self.results = []

    def _report_progress(self, message: str):
        """Report progress via callback if available."""
        logger.info(message)
        if self.progress_callback:
            try:
                self.progress_callback(message)
            except Exception:
                pass  # Never let callback errors break the audit

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
            return [
                TestResult(
                    name=f"{category} (ERROR): {self.table_name}",
                    status=CheckStatus.ERROR,
                    message=f"Check crashed: {type(e).__name__}: {e}",
                    details={"exception": str(e), "category": category},
                )
            ]

    def _validate_dataframes(self) -> bool:
        """Validate source and target DataFrames before running checks."""
        # Check for None DataFrames
        if self.src_df is None or self.tgt_df is None:
            which = []
            if self.src_df is None:
                which.append("source")
            if self.tgt_df is None:
                which.append("target")
            self.results.append(
                TestResult(
                    name=f"DataFrame Validation: {self.table_name}",
                    status=CheckStatus.FAIL,
                    message=f"Cannot run checks — {' and '.join(which)} DataFrame is None for table '{self.table_name}'.",
                )
            )
            return False

        # Check for non-DataFrame types
        if not isinstance(self.src_df, pd.DataFrame) or not isinstance(
            self.tgt_df, pd.DataFrame
        ):
            self.results.append(
                TestResult(
                    name=f"DataFrame Validation: {self.table_name}",
                    status=CheckStatus.FAIL,
                    message=f"Invalid data type — expected DataFrame, got source={type(self.src_df).__name__}, target={type(self.tgt_df).__name__}.",
                )
            )
            return False

        # Warn on empty DataFrames but allow checks to proceed
        if self.src_df.empty and self.tgt_df.empty:
            logger.warning(
                f"Both source and target DataFrames are empty for '{self.table_name}'"
            )
        elif self.src_df.empty:
            logger.warning(
                f"Source DataFrame is empty for '{self.table_name}' (target has {len(self.tgt_df)} rows)"
            )
        elif self.tgt_df.empty:
            logger.warning(
                f"Target DataFrame is empty for '{self.table_name}' (source has {len(self.src_df)} rows)"
            )

        return True

    def _run_volume_checks(self, check_registry):
        for fn in check_registry.get("volume", []):
            self.results.extend(
                self._safe_run(
                    "Volume Check",
                    fn,
                    self.table_name,
                    self.src_df,
                    self.tgt_df,
                    self.volume_tolerance,
                )
            )

    def _run_identity_checks(self):
        pk = getattr(self.meta, "primary_key", None)
        if not (pk and pk in self.src_df.columns and pk in self.tgt_df.columns):
            return

        try:
            src_ids = set(self.src_df[pk].dropna().unique())
            tgt_ids = set(self.tgt_df[pk].dropna().unique())

            overlap = src_ids.intersection(tgt_ids)
            overlap_pct = (len(overlap) / len(src_ids) * 100) if src_ids else 0

            status = (
                CheckStatus.PASS
                if overlap_pct >= self.identity_overlap_threshold
                else (CheckStatus.WARN if overlap_pct > 0 else CheckStatus.FAIL)
            )

            message = (
                f"Identity Overlap: {overlap_pct:.2f}% of source IDs found in target."
            )
            if overlap_pct == 0:
                message = "CRITICAL: 0% overlap detected! Source and Target share NO Primary Keys."

            # Note NULL PKs as a separate warning
            src_null_pks = self.src_df[pk].isnull().sum()
            tgt_null_pks = self.tgt_df[pk].isnull().sum()
            if src_null_pks > 0 or tgt_null_pks > 0:
                message += (
                    f" (NULL PK values: source={src_null_pks}, target={tgt_null_pks})"
                )

            self.results.append(
                TestResult(
                    name=f"Identity Check: {self.table_name}",
                    status=status,
                    message=message,
                    details={
                        "overlap_pct": overlap_pct,
                        "common_rows": len(overlap),
                        "src_null_pks": int(src_null_pks),
                        "tgt_null_pks": int(tgt_null_pks),
                    },
                )
            )
        except Exception as e:
            logger.error(
                f"Identity check failed for '{self.table_name}': {e}", exc_info=True
            )
            self.results.append(
                TestResult(
                    name=f"Identity Check (ERROR): {self.table_name}",
                    status=CheckStatus.ERROR,
                    message=f"Identity check crashed: {type(e).__name__}: {e}",
                )
            )

    def _run_aggregate_checks(self, check_registry):
        for col in getattr(self.meta, "aggregates", []):
            try:
                # Handle column mapping for complex mappings
                src_col = col
                tgt_col = col
                if (
                    hasattr(self.meta, "aggregate_column_mapping")
                    and self.meta.aggregate_column_mapping
                ):
                    if col in self.meta.aggregate_column_mapping.values():
                        src_col = next(
                            k
                            for k, v in self.meta.aggregate_column_mapping.items()
                            if v == col
                        )
                    elif col in self.meta.aggregate_column_mapping:
                        src_col = self.meta.aggregate_column_mapping[col]

                # Check if columns exist in dataframes
                if src_col not in self.src_df.columns:
                    self.results.append(
                        TestResult(
                            name=f"Aggregate check (Source Column Missing): {src_col}",
                            status=CheckStatus.FAIL,
                            message=f"Source column '{src_col}' not found in table '{self.table_name}'. Available columns: {list(self.src_df.columns[:10])}{'...' if len(self.src_df.columns) > 10 else ''}",
                        )
                    )
                    continue

                if tgt_col not in self.tgt_df.columns:
                    self.results.append(
                        TestResult(
                            name=f"Aggregate Check: {self.table_name} - {col}",
                            status=CheckStatus.WARN,
                            message=f"Target column '{tgt_col}' not found in table '{self.table_name}'. Available columns: {list(self.tgt_df.columns[:10])}{'...' if len(self.tgt_df.columns) > 10 else ''}",
                        )
                    )
                    continue

                # Data Quality: Check for non-numeric junk in a supposedly numeric column
                tgt_vals_coerced = pd.to_numeric(self.tgt_df[tgt_col], errors="coerce")
                junk_mask = self.tgt_df[tgt_col].notna() & tgt_vals_coerced.isna()
                junk_count = int(junk_mask.sum())

                if junk_count > 0:
                    sample_values = self.tgt_df.loc[junk_mask, tgt_col].head(5).tolist()
                    self.results.append(
                        TestResult(
                            name=f"Data Quality: {self.table_name}.{tgt_col}",
                            status=CheckStatus.FAIL,
                            message=f"Found {junk_count} non-numeric junk values in target column '{tgt_col}'. Samples: {sample_values}",
                            details={
                                "junk_rows": junk_count,
                                "sample_values": sample_values,
                            },
                        )
                    )

                for fn in check_registry.get("aggregates", []):
                    results = self._safe_run(
                        f"Aggregate Check ({col})",
                        fn,
                        self.src_df,
                        self.tgt_df,
                        src_col,
                        self.table_name,
                        self.aggregate_tolerance,
                    )
                    # Update result to show target column name if different
                    if src_col != tgt_col:
                        for r in results:
                            if hasattr(r, "name"):
                                r.name = r.name.replace(
                                    src_col, f"{src_col}->{tgt_col}"
                                )
                    self.results.extend(results)

            except Exception as e:
                logger.error(
                    f"Aggregate check for column '{col}' on '{self.table_name}' failed: {e}",
                    exc_info=True,
                )
                self.results.append(
                    TestResult(
                        name=f"Aggregate Check (ERROR): {self.table_name}.{col}",
                        status=CheckStatus.ERROR,
                        message=f"Aggregate check crashed for column '{col}': {type(e).__name__}: {e}",
                    )
                )

    def _run_mapping_checks(self, check_registry):
        for mapping in getattr(self.meta, "mappings", []):
            for fn in check_registry.get("mappings", []):
                self.results.extend(
                    self._safe_run(
                        "Mapping Check",
                        fn,
                        self.tgt_df,
                        mapping.columns,
                        mapping.allowed_values,
                        self.table_name,
                    )
                )

    def _run_relationship_checks(self, check_registry):
        from core.audit.loader import load_table

        for rel in getattr(self.meta, "relationships", []):
            # Load the actual parent (reference) table
            parent_target = rel.parent.get("target")
            if parent_target:
                try:
                    self._report_progress(
                        f"Loading parent table '{parent_target}' for relationship check"
                    )
                    parent_df = load_table(parent_target)
                except Exception as e:
                    logger.error(
                        f"Failed to load parent table '{parent_target}': {e}",
                        exc_info=True,
                    )
                    self.results.append(
                        TestResult(
                            name=f"Relationship Check (ERROR): {self.table_name}",
                            status=CheckStatus.ERROR,
                            message=(
                                f"Could not load parent table '{parent_target}': "
                                f"{type(e).__name__}: {e}"
                            ),
                        )
                    )
                    continue
            else:
                # Fallback: use tgt_df if no parent target specified
                logger.warning(
                    f"No parent target specified for relationship on '{self.table_name}', "
                    f"using target DataFrame as fallback"
                )
                parent_df = self.tgt_df

            for fn in check_registry.get("relationships", []):
                self.results.extend(
                    self._safe_run(
                        "Relationship Check",
                        fn,
                        self.tgt_df,  # child_df
                        parent_df,  # parent_df (loaded from reference table)
                        rel.child["fk_column"],
                        rel.parent["pk_column"],
                        self.table_name,
                    )
                )

    def _run_data_constraint_checks(self):
        from checks.data_constraints import check_data_constraints

        for col, constraints in getattr(self.meta, "data_constraints", {}).items():
            if isinstance(constraints, str):
                constraints = [constraints]
            self.results.extend(
                self._safe_run(
                    f"Data Constraint Check ({col})",
                    check_data_constraints,
                    self.tgt_df,
                    {col: constraints},
                    self.table_name,
                )
            )

    def execute_all(self):
        from core.audit.check_registry import CHECK_REGISTRY

        # --- Validate DataFrames before running any checks ---
        if not self._validate_dataframes():
            logger.error(
                f"Aborting checks for '{self.table_name}' due to invalid DataFrames"
            )
            return self.results

        steps = [
            ("Volume checks", lambda: self._run_volume_checks(CHECK_REGISTRY)),
            ("Identity checks", lambda: self._run_identity_checks()),
            ("Aggregate checks", lambda: self._run_aggregate_checks(CHECK_REGISTRY)),
            ("Mapping checks", lambda: self._run_mapping_checks(CHECK_REGISTRY)),
            (
                "Relationship checks",
                lambda: self._run_relationship_checks(CHECK_REGISTRY),
            ),
            ("Data constraint checks", lambda: self._run_data_constraint_checks()),
        ]

        for i, (step_name, step_fn) in enumerate(steps, 1):
            self._report_progress(
                f"[{self.table_name}] Running {step_name} ({i}/{len(steps)})"
            )
            step_fn()

        self._report_progress(f"[{self.table_name}] All checks complete")
        return self.results

    def execute_chunked(
        self,
        src_iter,
        tgt_iter,
        chunk_size: int = 10000,
    ):
        """Execute audit checks on chunked/streamed DataFrames.

        Useful for large datasets that cannot fit in memory.
        Accumulates chunks first, then runs standard checks.

        Args:
            src_iter: Iterator of source DataFrame chunks.
            tgt_iter: Iterator of target DataFrame chunks.
            chunk_size: Expected chunk size (for logging).

        Returns:
            List of TestResult objects.
        """
        self._report_progress(
            f"[{self.table_name}] Starting chunked processing (chunk_size={chunk_size})"
        )

        # Accumulate chunks into full DataFrames
        src_chunks = []
        tgt_chunks = []
        src_row_count = 0
        tgt_row_count = 0

        for i, chunk in enumerate(src_iter):
            src_chunks.append(chunk)
            src_row_count += len(chunk)
            self._report_progress(
                f"[{self.table_name}] Loaded source chunk {i + 1} "
                f"({len(chunk)} rows, total: {src_row_count})"
            )

        for i, chunk in enumerate(tgt_iter):
            tgt_chunks.append(chunk)
            tgt_row_count += len(chunk)
            self._report_progress(
                f"[{self.table_name}] Loaded target chunk {i + 1} "
                f"({len(chunk)} rows, total: {tgt_row_count})"
            )

        # Merge chunks
        self.src_df = (
            pd.concat(src_chunks, ignore_index=True) if src_chunks else pd.DataFrame()
        )
        self.tgt_df = (
            pd.concat(tgt_chunks, ignore_index=True) if tgt_chunks else pd.DataFrame()
        )

        self._report_progress(
            f"[{self.table_name}] Chunked loading complete: "
            f"source={src_row_count} rows, target={tgt_row_count} rows"
        )

        return self.execute_all()
