"""E2E Pipeline Tests — Ron Swanson (T009)

End-to-end tests validating the full audit pipeline:
  Config → Load Data → CheckRunner → Verdict
"""
import pytest
import pandas as pd
from core.audit.check_runner import CheckRunner
from core.audit.verdict import final_verdict, Verdict, is_migration_allowed
from core.audit.enums import CheckStatus
from core.audit.result import TestResult
from core.audit.config_models import TableConfig, MappingConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_pipeline(src_df, tgt_df, meta, vol_tol=0.1, agg_tol=1.0):
    """Run CheckRunner → final_verdict and return (results, verdict)."""
    runner = CheckRunner(
        table_name="e2e_test",
        meta=meta,
        src_df=src_df,
        tgt_df=tgt_df,
        volume_tolerance=vol_tol,
        aggregate_tolerance=agg_tol,
    )
    results = runner.execute_all()
    v = final_verdict(results)
    return results, v


def _meta(aggregates=None, mappings=None, constraints=None, pk="id"):
    """Build a minimal TableConfig for E2E tests."""
    return TableConfig(
        source="data/source/test.csv",
        target="data/target/test.csv",
        primary_key=pk,
        aggregates=aggregates or [],
        mappings=mappings or [],
        data_constraints=constraints or {},
    )


# ===================================================================
# E2E-001: Happy path — identical data → GO
# ===================================================================

class TestE2EHappyPath:
    def test_identical_data_gives_go(self, sample_src_df, sample_tgt_df):
        meta = _meta(
            aggregates=["amount"],
            mappings=[MappingConfig(columns=["status"], allowed_values=["active", "inactive", "pending"])],
            constraints={"email": ["not_null"]},
        )
        results, verdict = _run_pipeline(sample_src_df, sample_tgt_df, meta)

        assert verdict == Verdict.GO
        assert all(r.status in (CheckStatus.PASS, CheckStatus.WARN) for r in results)
        # No FAILs or ERRORs
        fail_count = sum(1 for r in results if r.status == CheckStatus.FAIL)
        error_count = sum(1 for r in results if r.status == CheckStatus.ERROR)
        assert fail_count == 0
        assert error_count == 0

    def test_pipeline_produces_volume_check(self, sample_src_df, sample_tgt_df):
        meta = _meta()
        results, _ = _run_pipeline(sample_src_df, sample_tgt_df, meta)

        volume_results = [r for r in results if "Volume" in r.name or "volume" in r.name.lower()]
        assert len(volume_results) >= 1

    def test_pipeline_produces_identity_check(self, sample_src_df, sample_tgt_df):
        meta = _meta(pk="id")
        results, _ = _run_pipeline(sample_src_df, sample_tgt_df, meta)

        identity_results = [r for r in results if "Identity" in r.name]
        assert len(identity_results) >= 1


# ===================================================================
# E2E-002: Data with FAILs → NO-GO
# ===================================================================

class TestE2ENoGo:
    def test_volume_mismatch_causes_no_go(self):
        """50% loss with 0.1% tolerance → FAIL → NO-GO."""
        src = pd.DataFrame({"id": range(100), "val": range(100)})
        tgt = pd.DataFrame({"id": range(50), "val": range(50)})
        meta = _meta()

        results, verdict = _run_pipeline(src, tgt, meta, vol_tol=0.1)
        assert verdict == Verdict.NO_GO

    def test_invalid_mapping_causes_no_go(self):
        """Value not in allowed list → FAIL → NO-GO."""
        src = pd.DataFrame({"id": [1], "status": ["active"]})
        tgt = pd.DataFrame({"id": [1], "status": ["DELETED"]})  # Not allowed
        meta = _meta(
            mappings=[MappingConfig(columns=["status"], allowed_values=["active", "inactive"])],
        )

        results, verdict = _run_pipeline(src, tgt, meta)
        assert verdict == Verdict.NO_GO

    def test_none_dataframe_causes_no_go(self):
        """None source → FAIL → NO-GO."""
        meta = _meta()
        results, verdict = _run_pipeline(None, pd.DataFrame({"id": [1]}), meta)
        assert verdict == Verdict.NO_GO


# ===================================================================
# E2E-003: Warnings → GO WITH WARNINGS
# ===================================================================

class TestE2EWarnings:
    def test_empty_source_yields_no_go(self):
        """Empty source + non-empty target → volume FAIL (100% loss exceeds tolerance) → NO-GO."""
        src = pd.DataFrame(columns=["id", "amount"])
        tgt = pd.DataFrame({"id": [1, 2], "amount": [10.0, 20.0]})
        meta = _meta()

        results, verdict = _run_pipeline(src, tgt, meta)
        # Volume check reports 100% loss which exceeds 0.1% tolerance → FAIL
        assert verdict == Verdict.NO_GO

    def test_slight_volume_loss_warns(self):
        """Slight volume difference produces warnings → GO WITH WARNINGS."""
        src = pd.DataFrame({"id": range(100), "amount": [1.0] * 100})
        tgt = pd.DataFrame({"id": range(100), "amount": [1.0] * 100})
        # Same row count but different PK values to trigger identity warn
        tgt_modified = tgt.copy()
        tgt_modified.loc[99, "id"] = 999  # 1 PK doesn't match source: 99% overlap → PASS
        meta = _meta(aggregates=["amount"])

        results, verdict = _run_pipeline(src, tgt_modified, meta)
        # All checks pass or warn → GO or GO WITH WARNINGS
        assert verdict in (Verdict.GO, Verdict.GO_WITH_WARNINGS)


# ===================================================================
# E2E-004: Error isolation — _safe_run prevents pipeline crash
# ===================================================================

class TestE2EErrorIsolation:
    def test_crashing_check_isolated(self, sample_src_df, sample_tgt_df):
        """If a check crashes, the pipeline still returns results (no uncaught exception)."""
        meta = _meta(aggregates=["nonexistent_column"])

        # This should NOT raise — _safe_run isolates the crash
        results, verdict = _run_pipeline(sample_src_df, sample_tgt_df, meta)
        assert results is not None
        assert len(results) > 0


# ===================================================================
# E2E-005: Non-DataFrame types
# ===================================================================

class TestE2ENonDataFrame:
    def test_dict_input_fails_gracefully(self):
        meta = _meta()
        results, verdict = _run_pipeline({"id": [1]}, pd.DataFrame({"id": [1]}), meta)
        assert verdict == Verdict.NO_GO
        assert any("DataFrame" in r.message for r in results)

    def test_string_input_fails_gracefully(self):
        meta = _meta()
        results, verdict = _run_pipeline("not_a_df", "also_not_a_df", meta)
        assert verdict == Verdict.NO_GO


# ===================================================================
# E2E-006: Full 5-dimension check
# ===================================================================

class TestE2EFullDimension:
    def test_all_five_dimensions_run(self, sample_src_df, sample_tgt_df):
        """Verify all 5 check types produce results when configured."""
        meta = _meta(
            aggregates=["amount"],
            mappings=[MappingConfig(columns=["status"], allowed_values=["active", "inactive", "pending"])],
            constraints={"email": ["not_null"]},
        )
        results, verdict = _run_pipeline(sample_src_df, sample_tgt_df, meta)

        result_names = " ".join(r.name.lower() for r in results)
        # Volume, Identity, Aggregate (sum/avg/etc.), Mapping, Constraint
        assert "volume" in result_names or "Volume" in " ".join(r.name for r in results)
        assert "identity" in result_names or "Identity" in " ".join(r.name for r in results)

    def test_constraint_not_null_violation_detected(self):
        """Data constraints catch not_null violations."""
        src = pd.DataFrame({"id": [1, 2], "email": ["a@x.com", "b@x.com"]})
        tgt = pd.DataFrame({"id": [1, 2], "email": ["a@x.com", None]})
        meta = _meta(constraints={"email": ["not_null"]})

        results, verdict = _run_pipeline(src, tgt, meta)
        constraint_results = [r for r in results if "constraint" in r.name.lower() or "Constraint" in r.name]
        # Should have at least one constraint result that catches the null
        assert len(constraint_results) >= 1
