import json
import os
import shutil
from datetime import datetime, timedelta
from typing import Any


class ComplianceEngine:
    """Simple compliance utility with retention and audit-trail helpers.

    This module is intentionally lightweight for MVP but provides hooks for
    retention policies and writing audit records. The real production system
    would likely push these into a database or external service.
    """

    OUTPUT_DIR = "outputs"
    AUDIT_LOG_PATH = "logs/compliance_audit.jsonl"

    @classmethod
    def purge_old_reports(cls, days: int = 30) -> None:
        """Delete report directories older than ``days`` days.

        The naming convention for report folders is ``YYYYMMDD_HHMMSS_<id>``
        so we parse the prefix to determine age. This logic is used by the
        nightly retention job (T006/T009).
        """
        cutoff = datetime.now() - timedelta(days=days)
        if not os.path.isdir(cls.OUTPUT_DIR):
            return

        for entry in os.listdir(cls.OUTPUT_DIR):
            path = os.path.join(cls.OUTPUT_DIR, entry)
            if not os.path.isdir(path):
                continue
            try:
                date_str = entry.split("_")[0]
                dt = datetime.strptime(date_str, "%Y%m%d")
            except Exception:  # malformed folder name
                continue
            if dt < cutoff:
                shutil.rmtree(path)

    @classmethod
    def log_event(cls, event: str, **data: Any) -> None:
        """Append a compliance-related event to the audit log."""
        os.makedirs(os.path.dirname(cls.AUDIT_LOG_PATH), exist_ok=True)
        record = {"timestamp": datetime.utcnow().isoformat() + "Z", "event": event}
        record.update(data)
        with open(cls.AUDIT_LOG_PATH, "a") as f:
            f.write(json.dumps(record) + "\n")
