from dataclasses import dataclass
from typing import Dict, List

from core.audit.enums import CheckStatus
from core.audit.result import TestResult


@dataclass
class TableAuditResult:
    table_name: str
    checks: List[TestResult]
    summary: Dict[CheckStatus, int]

    @classmethod
    def from_checks(cls, table_name: str, checks: List[TestResult]):
        summary = {
            CheckStatus.PASS: 0,
            CheckStatus.WARN: 0,
            CheckStatus.FAIL: 0,
        }

        for check in checks:
            summary[check.status] += 1

        return cls(table_name=table_name, checks=checks, summary=summary)
