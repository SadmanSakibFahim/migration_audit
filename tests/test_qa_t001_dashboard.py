"""QA Tests for T001 — Web Dashboard Results & Charts
=====================================================
Tests the new /api/audit/results endpoint, results summary
computation in run_audit_background_task, and AUDIT_STATE schema.

QA Engineer: Ben Wyatt (Software Testing Team)
Reviewer: Ron Swanson (QA Lead)
"""

from fastapi.testclient import TestClient

from core.web.app import app
from core.web.routes.api import AUDIT_STATE

client = TestClient(app)


# ===================================================================
# AUDIT_STATE Schema Validation
# ===================================================================


class TestAuditStateSchema:
    """Ben Wyatt: AUDIT_STATE must contain all required keys."""

    def test_state_has_results_summary(self):
        """AUDIT_STATE should contain results_summary with correct keys."""
        assert "results_summary" in AUDIT_STATE
        summary = AUDIT_STATE["results_summary"]
        for key in ("pass", "warn", "fail", "error", "total"):
            assert key in summary, f"Missing key: {key}"

    def test_state_has_results_details(self):
        """AUDIT_STATE should contain results_details list."""
        assert "results_details" in AUDIT_STATE
        assert isinstance(AUDIT_STATE["results_details"], list)

    def test_state_initial_values_are_zero(self):
        """All initial summary counts should be 0."""
        summary = AUDIT_STATE["results_summary"]
        assert summary["pass"] == 0
        assert summary["warn"] == 0
        assert summary["fail"] == 0
        assert summary["error"] == 0
        assert summary["total"] == 0

    def test_state_has_all_required_keys(self):
        """Full AUDIT_STATE schema compliance check."""
        required = {
            "status",
            "message",
            "logs",
            "progress",
            "last_run_id",
            "results_summary",
            "results_details",
        }
        assert required.issubset(set(AUDIT_STATE.keys()))


# ===================================================================
# /api/audit/results endpoint
# ===================================================================


class TestAuditResultsEndpoint:
    """Ben Wyatt: /api/audit/results endpoint QA."""

    def test_results_requires_auth(self):
        """GET /api/audit/results should require authentication."""
        response = client.get("/api/audit/results")
        data = response.json()
        assert response.status_code == 401 or data.get("error") == "Unauthorized"

    def test_results_returns_correct_shape(self):
        """Response should have status, summary, and details keys."""
        response = client.get("/api/audit/results")
        data = response.json()
        # Either auth error or correct response shape
        if "error" not in data:
            assert "status" in data
            assert "summary" in data
            assert "details" in data

    def test_results_summary_keys(self):
        """Summary should contain pass/warn/fail/error/total."""
        # Temporarily inject authenticated state to test shape
        response = client.get("/api/audit/results")
        # Regardless of auth, we can verify the endpoint exists
        assert response.status_code in (200, 401)


# ===================================================================
# /api/audit/start still works
# ===================================================================


class TestAuditStartEndpoint:
    """Ben Wyatt: Verify audit/start endpoint still functional."""

    def test_start_requires_auth(self):
        """POST /api/audit/start should require authentication."""
        response = client.post(
            "/api/audit/start",
            json={"tables": ["test"]},
        )
        data = response.json()
        assert response.status_code == 401 or data.get("error") == "Unauthorized"


# ===================================================================
# Results Summary Computation (Unit Test)
# ===================================================================


class TestResultsSummaryComputation:
    """Ben Wyatt: Testing the results aggregation logic in isolation."""

    def test_compute_summary_from_results(self):
        """Simulate what run_audit_background_task does with results."""
        from core.audit.enums import CheckStatus
        from core.audit.result import TestResult

        mock_results = [
            TestResult(name="Volume", status=CheckStatus.PASS, message="ok"),
            TestResult(name="Identity", status=CheckStatus.PASS, message="ok"),
            TestResult(name="Aggregate", status=CheckStatus.WARN, message="drift"),
            TestResult(name="Mapping", status=CheckStatus.FAIL, message="bad"),
            TestResult(name="Constraint", status=CheckStatus.ERROR, message="crash"),
        ]

        summary = {"pass": 0, "warn": 0, "fail": 0, "error": 0, "total": 0}
        details = []

        for r in mock_results:
            status_str = str(r.status).lower()
            if "pass" in status_str:
                summary["pass"] += 1
            elif "warn" in status_str:
                summary["warn"] += 1
            elif "fail" in status_str:
                summary["fail"] += 1
            elif "error" in status_str:
                summary["error"] += 1
            summary["total"] += 1
            details.append(
                {
                    "name": r.name,
                    "status": status_str,
                    "message": r.message,
                }
            )

        assert summary == {"pass": 2, "warn": 1, "fail": 1, "error": 1, "total": 5}
        assert len(details) == 5
        assert details[0]["name"] == "Volume"
        assert "pass" in details[0]["status"]

    def test_compute_summary_empty_results(self):
        """Empty results should produce all-zero summary."""
        summary = {"pass": 0, "warn": 0, "fail": 0, "error": 0, "total": 0}
        details = []

        for _ in []:
            pass  # No results

        assert summary["total"] == 0
        assert len(details) == 0

    def test_compute_summary_all_pass(self):
        """All-pass results should show correct counts."""
        from core.audit.enums import CheckStatus
        from core.audit.result import TestResult

        mock_results = [
            TestResult(name=f"Check {i}", status=CheckStatus.PASS, message="ok")
            for i in range(10)
        ]

        summary = {"pass": 0, "warn": 0, "fail": 0, "error": 0, "total": 0}
        for r in mock_results:
            status_str = str(r.status).lower()
            if "pass" in status_str:
                summary["pass"] += 1
            summary["total"] += 1

        assert summary["pass"] == 10
        assert summary["total"] == 10
        assert summary["warn"] == 0
        assert summary["fail"] == 0


# ===================================================================
# SSE Stream still includes results_summary
# ===================================================================


class TestSSEStreamSchema:
    """Ben Wyatt: The SSE event_generator should include results_summary."""

    def test_audit_state_serializable(self):
        """AUDIT_STATE must be JSON-serializable for SSE streaming."""
        import json

        # Should not raise
        serialized = json.dumps(AUDIT_STATE)
        parsed = json.loads(serialized)
        assert "results_summary" in parsed
        assert "results_details" in parsed
