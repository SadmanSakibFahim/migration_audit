"""Verdict Logic Tests

Tests for final_verdict() and is_migration_allowed() in core/audit/verdict.py.
Covers all verdict outcomes: GO, GO WITH WARNINGS, NO-GO, ERROR, and empty.
"""

from core.audit.enums import CheckStatus
from core.audit.result import TestResult
from core.audit.verdict import Verdict, final_verdict, is_migration_allowed


def _r(status: CheckStatus, name: str = "test") -> TestResult:
    return TestResult(name=name, status=status, message=f"{status.value}")


# ===================================================================
# final_verdict
# ===================================================================


class TestFinalVerdict:
    def test_all_pass_returns_go(self):
        results = [_r(CheckStatus.PASS), _r(CheckStatus.PASS), _r(CheckStatus.PASS)]
        assert final_verdict(results) == Verdict.GO

    def test_single_pass_returns_go(self):
        assert final_verdict([_r(CheckStatus.PASS)]) == Verdict.GO

    def test_has_warn_no_fail_returns_go_with_warnings(self):
        results = [_r(CheckStatus.PASS), _r(CheckStatus.WARN), _r(CheckStatus.PASS)]
        assert final_verdict(results) == Verdict.GO_WITH_WARNINGS

    def test_all_warn_returns_go_with_warnings(self):
        results = [_r(CheckStatus.WARN), _r(CheckStatus.WARN)]
        assert final_verdict(results) == Verdict.GO_WITH_WARNINGS

    def test_has_fail_returns_no_go(self):
        results = [_r(CheckStatus.PASS), _r(CheckStatus.FAIL), _r(CheckStatus.PASS)]
        assert final_verdict(results) == Verdict.NO_GO

    def test_all_fail_returns_no_go(self):
        results = [_r(CheckStatus.FAIL), _r(CheckStatus.FAIL)]
        assert final_verdict(results) == Verdict.NO_GO

    def test_fail_overrides_warn(self):
        results = [_r(CheckStatus.WARN), _r(CheckStatus.FAIL)]
        assert final_verdict(results) == Verdict.NO_GO

    def test_error_returns_error(self):
        results = [_r(CheckStatus.PASS), _r(CheckStatus.ERROR)]
        assert final_verdict(results) == Verdict.ERROR

    def test_error_overrides_warn(self):
        results = [_r(CheckStatus.WARN), _r(CheckStatus.ERROR)]
        assert final_verdict(results) == Verdict.ERROR

    def test_empty_results_returns_no_go(self):
        assert final_verdict([]) == Verdict.NO_GO

    def test_none_like_empty(self):
        """Empty list → NO-GO (no checks ran)."""
        assert final_verdict([]) == Verdict.NO_GO


# ===================================================================
# is_migration_allowed
# ===================================================================


class TestIsMigrationAllowed:
    def test_go_is_allowed(self):
        assert is_migration_allowed(Verdict.GO) is True

    def test_go_with_warnings_is_allowed(self):
        assert is_migration_allowed(Verdict.GO_WITH_WARNINGS) is True

    def test_no_go_is_not_allowed(self):
        assert is_migration_allowed(Verdict.NO_GO) is False

    def test_error_is_not_allowed(self):
        assert is_migration_allowed(Verdict.ERROR) is False


# ===================================================================
# Verdict constants
# ===================================================================


class TestVerdictConstants:
    def test_go_value(self):
        assert Verdict.GO == "GO"

    def test_go_with_warnings_value(self):
        assert Verdict.GO_WITH_WARNINGS == "GO WITH WARNINGS"

    def test_no_go_value(self):
        assert Verdict.NO_GO == "NO-GO"

    def test_error_value(self):
        assert Verdict.ERROR == "ERROR"
