"""
CI/CD output serializer for migration audit results.

Converts audit TestResult objects into structured JSON
suitable for consumption by CI/CD pipelines, GitHub Actions,
and other automation tools.
"""

import json
from collections import Counter
from datetime import datetime, timezone
from typing import Dict, List, Optional

from core.audit.enums import CheckStatus
from core.audit.result import TestResult
from core.audit.verdict import Verdict, final_verdict


def serialize_check(result: TestResult) -> Dict:
    """Serialize a single TestResult to a JSON-friendly dict."""
    entry = {
        "name": result.name,
        "status": result.status.value,
        "message": result.message,
    }
    if result.details:
        entry["details"] = result.details
    if result.metrics:
        entry["metrics"] = result.metrics
    return entry


def build_ci_report(results: List[TestResult]) -> Dict:
    """
    Build a structured CI report from audit results.

    Returns a dict with:
        - verdict: str — final audit verdict
        - summary: dict — counts of PASS/WARN/FAIL/ERROR
        - timestamp: str — ISO 8601 UTC timestamp
        - total_checks: int — number of checks executed
        - checks: list — serialized individual check results
    """
    verdict = final_verdict(results)
    status_counts = Counter(r.status for r in results)

    return {
        "verdict": verdict,
        "summary": {
            "pass": status_counts.get(CheckStatus.PASS, 0),
            "warn": status_counts.get(CheckStatus.WARN, 0),
            "fail": status_counts.get(CheckStatus.FAIL, 0),
            "error": status_counts.get(CheckStatus.ERROR, 0),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_checks": len(results),
        "checks": [serialize_check(r) for r in results],
    }


def write_ci_report(
    results: List[TestResult],
    output_path: str,
) -> Dict:
    """
    Build and write CI report JSON to disk.

    Args:
        results: List of TestResult objects from the audit.
        output_path: File path to write JSON report.

    Returns:
        The report dict (for further processing / exit code logic).
    """
    report = build_ci_report(results)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return report


def verdict_exit_code(verdict: str, fail_on_warnings: bool = False) -> int:
    """
    Map an audit verdict to a CI exit code.

    Args:
        verdict: The verdict string from Verdict class.
        fail_on_warnings: If True, GO WITH WARNINGS also returns 1.

    Returns:
        0 for passing verdicts, 1 for blocking verdicts.
    """
    if verdict in (Verdict.NO_GO, Verdict.ERROR):
        return 1
    if fail_on_warnings and verdict == Verdict.GO_WITH_WARNINGS:
        return 1
    return 0
