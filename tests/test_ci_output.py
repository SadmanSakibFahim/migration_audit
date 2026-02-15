"""
Unit tests for core.audit.ci_output module.

Tests JSON serialization, verdict-to-exit-code mapping,
and report building with various result combinations.
"""

import json
import os
import tempfile
from datetime import datetime

import pytest

from core.audit.ci_output import (
    build_ci_report,
    serialize_check,
    verdict_exit_code,
    write_ci_report,
)
from core.audit.enums import CheckStatus
from core.audit.result import TestResult
from core.audit.verdict import Verdict


# ── Fixtures ──────────────────────────────────────────────


@pytest.fixture
def passing_results():
    """All checks pass."""
    return [
        TestResult(name="volume_check_users", status=CheckStatus.PASS, message="Row count match: 1000/1000"),
        TestResult(name="aggregate_check_users_age", status=CheckStatus.PASS, message="Aggregate within tolerance"),
        TestResult(name="mapping_check_users_status", status=CheckStatus.PASS, message="All values valid"),
    ]


@pytest.fixture
def mixed_results():
    """Mix of PASS, WARN, and FAIL."""
    return [
        TestResult(name="volume_check_users", status=CheckStatus.PASS, message="OK"),
        TestResult(name="aggregate_check_orders", status=CheckStatus.WARN, message="1.5% diff"),
        TestResult(name="mapping_check_orders_status", status=CheckStatus.FAIL, message="Invalid value: 'unknown'"),
    ]


@pytest.fixture
def error_results():
    """Infrastructure error."""
    return [
        TestResult(name="volume_check_users", status=CheckStatus.ERROR, message="Connection refused"),
    ]


@pytest.fixture
def result_with_details():
    """Result with details and metrics."""
    return TestResult(
        name="volume_check_users",
        status=CheckStatus.PASS,
        message="Row count match",
        details={"source_count": 1000, "target_count": 1000},
        metrics={"match_pct": 100.0},
    )


# ── serialize_check ───────────────────────────────────────


class TestSerializeCheck:
    def test_basic_serialization(self):
        result = TestResult(name="check_1", status=CheckStatus.PASS, message="OK")
        data = serialize_check(result)
        assert data["name"] == "check_1"
        assert data["status"] == "PASS"
        assert data["message"] == "OK"
        assert "details" not in data
        assert "metrics" not in data

    def test_serialization_with_details(self, result_with_details):
        data = serialize_check(result_with_details)
        assert data["details"] == {"source_count": 1000, "target_count": 1000}
        assert data["metrics"] == {"match_pct": 100.0}

    def test_serialization_fail_status(self):
        result = TestResult(name="check_fail", status=CheckStatus.FAIL, message="Bad")
        data = serialize_check(result)
        assert data["status"] == "FAIL"


# ── build_ci_report ───────────────────────────────────────


class TestBuildCiReport:
    def test_passing_report(self, passing_results):
        report = build_ci_report(passing_results)
        assert report["verdict"] == Verdict.GO
        assert report["summary"]["pass"] == 3
        assert report["summary"]["warn"] == 0
        assert report["summary"]["fail"] == 0
        assert report["summary"]["error"] == 0
        assert report["total_checks"] == 3
        assert len(report["checks"]) == 3

    def test_mixed_report(self, mixed_results):
        report = build_ci_report(mixed_results)
        assert report["verdict"] == Verdict.NO_GO
        assert report["summary"]["pass"] == 1
        assert report["summary"]["warn"] == 1
        assert report["summary"]["fail"] == 1

    def test_error_report(self, error_results):
        report = build_ci_report(error_results)
        assert report["verdict"] == Verdict.ERROR
        assert report["summary"]["error"] == 1

    def test_empty_results(self):
        report = build_ci_report([])
        assert report["verdict"] == Verdict.NO_GO
        assert report["total_checks"] == 0

    def test_timestamp_is_iso_format(self, passing_results):
        report = build_ci_report(passing_results)
        # Should not raise
        datetime.fromisoformat(report["timestamp"])

    def test_report_is_json_serializable(self, mixed_results):
        report = build_ci_report(mixed_results)
        # Must not raise
        json.dumps(report)


# ── write_ci_report ───────────────────────────────────────


class TestWriteCiReport:
    def test_writes_json_file(self, passing_results):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "audit_result.json")
            report = write_ci_report(passing_results, path)

            assert os.path.exists(path)
            with open(path) as f:
                loaded = json.load(f)
            assert loaded["verdict"] == Verdict.GO
            assert loaded["total_checks"] == 3

    def test_report_matches_return_value(self, mixed_results):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "result.json")
            report = write_ci_report(mixed_results, path)

            with open(path) as f:
                loaded = json.load(f)
            assert loaded["verdict"] == report["verdict"]
            assert loaded["total_checks"] == report["total_checks"]


# ── verdict_exit_code ─────────────────────────────────────


class TestVerdictExitCode:
    def test_go_returns_zero(self):
        assert verdict_exit_code(Verdict.GO) == 0

    def test_go_with_warnings_returns_zero_by_default(self):
        assert verdict_exit_code(Verdict.GO_WITH_WARNINGS) == 0

    def test_go_with_warnings_returns_one_when_strict(self):
        assert verdict_exit_code(Verdict.GO_WITH_WARNINGS, fail_on_warnings=True) == 1

    def test_no_go_returns_one(self):
        assert verdict_exit_code(Verdict.NO_GO) == 1

    def test_error_returns_one(self):
        assert verdict_exit_code(Verdict.ERROR) == 1

    def test_go_with_strict_still_returns_zero(self):
        assert verdict_exit_code(Verdict.GO, fail_on_warnings=True) == 0
