from typing import Any, Dict, List, Optional

import pandas as pd

from core.audit.enums import CheckStatus
from core.audit.logger import get_logger
from core.audit.result import TestResult

logger = get_logger(__name__)


class CheckRunner:
    def __init__(
        self,
        table_name: str,
        meta: Any,
        src_df: pd.DataFrame,
        tgt_df: pd.DataFrame,
        config: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Any] = None,
    ) -> None:
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

        self.results: List[TestResult] = []

    def _report_progress(self, message: str) -> None:
        """Report progress via callback if available."""
        logger.info(message)
        if self.progress_callback:
            try:
                self.progress_callback(message)
            except Exception:
                pass  # Never let callback errors break the audit

    def _normalize_result(self, result: Any) -> List[TestResult]:
        if result is None:
            return []
        if isinstance(result, list):
            return result
        return [result]

    def _safe_run(self, category: str, fn: Any, *args: Any, **kwargs: Any) -> List[TestResult]:
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

    def _run_volume_checks(self, check_registry: Dict[str, Any]) -> None:
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

    def _run_identity_checks(self) -> None:
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

    def _run_aggregate_checks(self, check_registry: Dict[str, Any]) -> None:
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

    def _run_mapping_checks(self, check_registry: Dict[str, Any]) -> None:
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

    def _run_relationship_checks(self, check_registry: Dict[str, Any]) -> None:
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

    def _run_data_constraint_checks(self) -> None:
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

    # ── Advanced Data Quality Checks ──────────────────────────────────────────

    def _run_string_checks(self) -> None:
        from checks.string_checks import (
            check_string_truncation,
            check_whitespace_corruption,
            check_encoding_corruption
        )

        for cfg in getattr(self.meta, "string_columns", []):
            col = cfg.column
            max_length = getattr(cfg, "max_length", None)
            
            # 1. Truncation Check
            self.results.extend(
                self._safe_run(
                    f"String Truncation Check ({col})",
                    check_string_truncation,
                    self.src_df,
                    self.tgt_df,
                    col,
                    self.table_name,
                    max_length,
                )
            )

            # 2. Whitespace Corruption Check
            if getattr(cfg, "check_whitespace", False):
                self.results.extend(
                    self._safe_run(
                        f"Whitespace Corruption Check ({col})",
                        check_whitespace_corruption,
                        self.src_df,
                        self.tgt_df,
                        col,
                        self.table_name,
                    )
                )

            # 3. Encoding Corruption Check
            if getattr(cfg, "check_encoding", False):
                self.results.extend(
                    self._safe_run(
                        f"Encoding Corruption Check ({col})",
                        check_encoding_corruption,
                        self.src_df,
                        self.tgt_df,
                        col,
                        self.table_name,
                    )
                )

    def _run_enum_checks(self) -> None:
        from checks.enum_checks import (
            check_enum_equivalence,
            check_categorical_distribution
        )

        for cfg in getattr(self.meta, "enum_columns", []):
            col = cfg.column
            mapping = getattr(cfg, "mapping", None)
            
            # 1. Equivalence Check
            self.results.extend(
                self._safe_run(
                    f"Enum Equivalence Check ({col})",
                    check_enum_equivalence,
                    self.src_df,
                    self.tgt_df,
                    col,
                    self.table_name,
                    mapping,
                )
            )

            # 2. Distribution Check
            if getattr(cfg, "check_distribution", False):
                tolerance = getattr(cfg, "distribution_tolerance_pct", 0.05)
                self.results.extend(
                    self._safe_run(
                        f"Categorical Distribution Check ({col})",
                        check_categorical_distribution,
                        self.src_df,
                        self.tgt_df,
                        col,
                        self.table_name,
                        tolerance,
                    )
                )

    def _run_datetime_checks(self) -> None:
        from checks.datetime_checks import check_timezone_consistency

        pk_column = getattr(self.meta, "primary_key", None)
        for cfg in getattr(self.meta, "datetime_columns", []):
            col = cfg.column
            expected_tz = getattr(cfg, "expected_tz", None)
            self.results.extend(
                self._safe_run(
                    f"Datetime/TZ Check ({col})",
                    check_timezone_consistency,
                    self.src_df,
                    self.tgt_df,
                    col,
                    self.table_name,
                    expected_tz,
                    pk_column,
                )
            )

    def _run_null_sentinel_checks(self) -> None:
        from checks.null_sentinel_checks import check_null_sentinel_equivalence

        for cfg in getattr(self.meta, "null_sentinels", []):
            col = cfg.column
            sentinels = cfg.sentinels
            self.results.extend(
                self._safe_run(
                    f"Null/Sentinel Check ({col})",
                    check_null_sentinel_equivalence,
                    self.src_df,
                    self.tgt_df,
                    col,
                    self.table_name,
                    sentinels,
                )
            )

    # ── Phase 2: Advanced Constraint Checks ───────────────────────────────────

    def _run_numeric_precision_checks(self) -> None:
        from checks.aggregates import check_numeric_precision

        for cfg in getattr(self.meta, "numeric_precision_columns", []):
            col = cfg.column
            precision = getattr(cfg, "expected_precision", None)
            scale = getattr(cfg, "expected_scale", None)
            self.results.extend(
                self._safe_run(
                    f"Numeric Precision Check ({col})",
                    check_numeric_precision,
                    self.src_df,
                    self.tgt_df,
                    col,
                    self.table_name,
                    precision,
                    scale,
                )
            )

    def _run_boolean_checks(self) -> None:
        from checks.enum_checks import check_boolean_normalization

        for cfg in getattr(self.meta, "boolean_columns", []):
            col = cfg.column
            t_vals = cfg.true_values
            f_vals = cfg.false_values
            self.results.extend(
                self._safe_run(
                    f"Boolean Normalization Check ({col})",
                    check_boolean_normalization,
                    self.src_df,
                    self.tgt_df,
                    col,
                    self.table_name,
                    t_vals,
                    f_vals,
                )
            )

    def _run_uniqueness_checks(self) -> None:
        from checks.data_constraints import check_uniqueness

        for col in getattr(self.meta, "unique_columns", []):
            self.results.extend(
                self._safe_run(
                    f"Uniqueness Check ({col})",
                    check_uniqueness,
                    self.src_df,
                    self.tgt_df,
                    col,
                    self.table_name,
                )
            )

    # ─────────────────────────────────────────────────────────────────────────

    def execute_all(self) -> List[TestResult]:
        from core.audit.check_registry import CHECK_REGISTRY

        # --- Validate DataFrames before running any checks ---
        if not self._validate_dataframes():
            logger.error(
                f"Aborting checks for '{self.table_name}' due to invalid DataFrames"
            )
            return self.results

        from typing import Callable
        steps: List[tuple[str, Callable[[], None]]] = [
            ("Volume checks", lambda: self._run_volume_checks(CHECK_REGISTRY)),
            ("Identity checks", lambda: self._run_identity_checks()),
            ("Aggregate checks", lambda: self._run_aggregate_checks(CHECK_REGISTRY)),
            ("Mapping checks", lambda: self._run_mapping_checks(CHECK_REGISTRY)),
            (
                "Relationship checks",
                lambda: self._run_relationship_checks(CHECK_REGISTRY),
            ),
            ("Data constraint checks", lambda: self._run_data_constraint_checks()),
            # Advanced data quality checks
            ("String truncation checks", lambda: self._run_string_checks()),
            ("Enum equivalence checks", lambda: self._run_enum_checks()),
            ("Datetime/TZ checks", lambda: self._run_datetime_checks()),
            ("Null/sentinel checks", lambda: self._run_null_sentinel_checks()),
            # Phase 2 checks
            ("Numeric precision checks", lambda: self._run_numeric_precision_checks()),
            ("Boolean checks", lambda: self._run_boolean_checks()),
            ("Uniqueness checks", lambda: self._run_uniqueness_checks()),
        ]

        for i, (step_name, step_fn) in enumerate(steps, 1):
            self._report_progress(
                f"[{self.table_name}] Running {step_name} ({i}/{len(steps)})"
            )
            step_fn()

        self._report_progress(f"[{self.table_name}] All checks complete")
        return self.results

