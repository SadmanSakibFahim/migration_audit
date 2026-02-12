"""CheckRunner Unit Tests — Leslie Knope (T014)

Tests for _safe_run(), _validate_dataframes(), _normalize_result(), and execute_all()
in core/audit/check_runner.py.
"""
import pytest
import pandas as pd
from core.audit.check_runner import CheckRunner
from core.audit.enums import CheckStatus
from core.audit.result import TestResult
from core.audit.config_models import TableConfig


def _meta(pk="id", aggregates=None):
    return TableConfig(
        source="test_src.csv",
        target="test_tgt.csv",
        primary_key=pk,
        aggregates=aggregates or [],
    )


def _runner(src_df=None, tgt_df=None, meta=None):
    if meta is None:
        meta = _meta()
    if src_df is None:
        src_df = pd.DataFrame({"id": [1, 2, 3]})
    if tgt_df is None:
        tgt_df = pd.DataFrame({"id": [1, 2, 3]})
    return CheckRunner("test_table", meta, src_df, tgt_df)


# ===================================================================
# _normalize_result
# ===================================================================

class TestNormalizeResult:
    def test_none_returns_empty_list(self):
        runner = _runner()
        assert runner._normalize_result(None) == []

    def test_single_result_wrapped_in_list(self):
        runner = _runner()
        r = TestResult(name="t", status=CheckStatus.PASS, message="ok")
        assert runner._normalize_result(r) == [r]

    def test_list_returned_as_is(self):
        runner = _runner()
        r = [TestResult(name="t", status=CheckStatus.PASS, message="ok")]
        assert runner._normalize_result(r) is r

    def test_empty_list_returned_as_is(self):
        runner = _runner()
        assert runner._normalize_result([]) == []


# ===================================================================
# _safe_run
# ===================================================================

class TestSafeRun:
    def test_normal_function_returns_results(self):
        runner = _runner()

        def good_fn():
            return TestResult(name="good", status=CheckStatus.PASS, message="ok")

        results = runner._safe_run("Test", good_fn)
        assert len(results) == 1
        assert results[0].status == CheckStatus.PASS

    def test_exception_returns_error_result(self):
        runner = _runner()

        def bad_fn():
            raise ValueError("test crash")

        results = runner._safe_run("Crashing Check", bad_fn)
        assert len(results) == 1
        assert results[0].status == CheckStatus.ERROR
        assert "test crash" in results[0].message
        assert "ValueError" in results[0].message

    def test_args_passed_through(self):
        runner = _runner()

        def fn_with_args(a, b, key=None):
            assert a == 1
            assert b == 2
            assert key == "val"
            return TestResult(name="args", status=CheckStatus.PASS, message="ok")

        results = runner._safe_run("Args Test", fn_with_args, 1, 2, key="val")
        assert results[0].status == CheckStatus.PASS

    def test_none_return_normalized(self):
        runner = _runner()

        def returns_none():
            return None

        results = runner._safe_run("None Return", returns_none)
        assert results == []

    def test_list_return_normalized(self):
        runner = _runner()

        def returns_list():
            return [
                TestResult(name="a", status=CheckStatus.PASS, message="ok"),
                TestResult(name="b", status=CheckStatus.WARN, message="warn"),
            ]

        results = runner._safe_run("List Return", returns_list)
        assert len(results) == 2


# ===================================================================
# _validate_dataframes
# ===================================================================

class TestValidateDataframes:
    def test_valid_dataframes_return_true(self):
        runner = _runner()
        assert runner._validate_dataframes() is True
        assert len(runner.results) == 0  # No warnings appended

    def test_none_source_returns_false(self):
        runner = _runner(src_df=None, tgt_df=pd.DataFrame({"id": [1]}))
        # Must set manually since _runner helper defaults
        runner.src_df = None
        assert runner._validate_dataframes() is False
        assert len(runner.results) == 1
        assert runner.results[0].status == CheckStatus.FAIL
        assert "source" in runner.results[0].message

    def test_none_target_returns_false(self):
        runner = _runner()
        runner.tgt_df = None
        assert runner._validate_dataframes() is False
        assert "target" in runner.results[0].message

    def test_both_none_returns_false(self):
        runner = _runner()
        runner.src_df = None
        runner.tgt_df = None
        assert runner._validate_dataframes() is False
        assert "source" in runner.results[0].message
        assert "target" in runner.results[0].message

    def test_non_dataframe_type_returns_false(self):
        runner = _runner()
        runner.src_df = {"id": [1, 2]}  # dict, not DataFrame
        assert runner._validate_dataframes() is False
        assert "dict" in runner.results[0].message

    def test_string_type_returns_false(self):
        runner = _runner()
        runner.tgt_df = "not_a_dataframe"
        assert runner._validate_dataframes() is False

    def test_empty_dataframes_return_true(self):
        """Empty but valid DataFrames are allowed (with logging)."""
        runner = _runner(
            src_df=pd.DataFrame(columns=["id"]),
            tgt_df=pd.DataFrame(columns=["id"]),
        )
        assert runner._validate_dataframes() is True
        # No FAIL results for empty — just logs
        assert len(runner.results) == 0


# ===================================================================
# execute_all
# ===================================================================

class TestExecuteAll:
    def test_returns_results_list(self, sample_src_df, sample_tgt_df):
        runner = _runner(src_df=sample_src_df, tgt_df=sample_tgt_df)
        results = runner.execute_all()
        assert isinstance(results, list)
        assert len(results) > 0

    def test_none_src_aborts_early(self):
        runner = _runner()
        runner.src_df = None
        results = runner.execute_all()
        # Should only have the validation FAIL result, no check results
        assert len(results) == 1
        assert results[0].status == CheckStatus.FAIL

    def test_with_aggregates(self, sample_src_df, sample_tgt_df):
        meta = _meta(aggregates=["amount"])
        runner = _runner(src_df=sample_src_df, tgt_df=sample_tgt_df, meta=meta)
        results = runner.execute_all()
        # Should have volume + identity + aggregate results
        assert len(results) > 2

    def test_missing_aggregate_column_reported(self, sample_src_df, sample_tgt_df):
        """Aggregate on non-existent column should produce a FAIL result, not crash."""
        meta = _meta(aggregates=["nonexistent_column_xyz"])
        runner = _runner(src_df=sample_src_df, tgt_df=sample_tgt_df, meta=meta)
        results = runner.execute_all()
        fail_results = [r for r in results if r.status == CheckStatus.FAIL]
        assert any("nonexistent_column_xyz" in r.message for r in fail_results)
