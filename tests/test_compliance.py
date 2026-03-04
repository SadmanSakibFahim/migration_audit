import json
import os
import pytest

import pandas as pd
from fastapi.testclient import TestClient

from core.sanitization.masking import DataSanitizer
from core.web.app import app

# Import after app so engine reflects the env var set in conftest
from core.auth.models import Base
from core.web.routes.auth import engine


@pytest.fixture(autouse=True)
def ensure_auth_tables():
    """Recreate auth tables on the current engine before each test."""
    from core.compliance.models import Base as ComplianceBase
    Base.metadata.drop_all(bind=engine)
    ComplianceBase.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    ComplianceBase.metadata.create_all(bind=engine)
    yield

def test_security_headers():
    with TestClient(app) as client:
        response = client.get("/")
        assert "Strict-Transport-Security" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-Content-Type-Options"] == "nosniff"

def test_data_sanitizer():
    sanitizer = DataSanitizer()
    df = pd.DataFrame(
        {
            "email": ["test@example.com"],
            "credit_card": ["1234-5678-9012-3456"],
            "normal_col": ["safe"],
        }
    )

    sanitized = sanitizer.sanitize(df)

    # Check Hashing
    assert sanitized["email"][0] != "test@example.com"
    assert len(sanitized["email"][0]) == 64  # SHA256 hex digest length

    # Check Dropping
    assert "credit_card" not in sanitized.columns

    # Check Retention
    assert "normal_col" in sanitized.columns
    assert sanitized["normal_col"][0] == "safe"


def test_audit_logging():
    # Trigger a login failure to generate a log
    with TestClient(app) as client:
        client.post("/login", data={"username": "test_audit_user", "password": "wrong"})

    # Check log file
    log_file = "logs/audit.jsonl"
    assert os.path.exists(log_file)

    found = False
    with open(log_file, "r") as f:
        for line in f:
            try:
                log = json.loads(line)
                if (
                    log.get("user_id") == "test_audit_user"
                    and log.get("action") == "LOGIN_FAILED"
                ):
                    found = True
                    break
            except json.JSONDecodeError:
                continue

    assert found, "Audit log entry for failed login not found"


def test_retention_purge(tmp_path, monkeypatch):
    # create dummy report directories with different dates
    base = tmp_path / "outputs"
    base.mkdir()
    old = base / "20260101_old"
    recent = base / "20260301_recent"
    old.mkdir()
    recent.mkdir()

    monkeypatch.setattr("core.compliance.engine.ComplianceEngine.OUTPUT_DIR", str(base))

    # purge reports older than 60 days (none should be removed since dates are synthetic)
    from core.compliance.engine import ComplianceEngine

    ComplianceEngine.purge_old_reports(days=30)
    # since 20260101 is definitely older than cutoff relative to now, it should be removed
    assert not old.exists()
    assert recent.exists()
