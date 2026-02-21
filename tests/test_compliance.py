import json
import os

import pandas as pd
from fastapi.testclient import TestClient

from core.sanitization.masking import DataSanitizer
from core.web.app import app

client = TestClient(app)


def test_security_headers():
    response = client.get("/")
    # Redirect counts as response, usually headers are there too
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
