import os
# Note: SECRET_KEY, AUTH_DB_URI, ALLOWED_HOSTS are set globally in conftest.py

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from core.web.app import app
import io

client = TestClient(app)

@pytest.fixture
def mock_auth():
    # Patch get_current_user dependency or the session middleware directly
    # Or just mock the route dependencies
    # fastapi TestClient doesn't easily mock request.session.get("user") unless we use middleware
    # Let's mock get_current_user in the router
    with patch("core.web.routes.api.get_current_user") as mock_user:
        mock_user.return_value = {"username": "admin", "role": "admin", "id": 1}
        yield mock_user

@pytest.fixture
def unauth_mock():
    with patch("core.web.routes.api.get_current_user") as mock_user:
        mock_user.return_value = None
        yield mock_user

def test_api_upload_unauthorized(unauth_mock):
    response = client.post("/api/upload")
    assert response.status_code == 401

def test_api_upload_authorized(mock_auth):
    # Test uploading dummy files — patch file I/O so audit.yaml is NOT modified on disk
    files = {
        'config': ('audit.yaml', io.BytesIO(b'tables:\n  test:\n    source: "a.csv"'), 'application/x-yaml'),
        'data_files': ('data.csv', io.BytesIO(b'id,val\n1,2'), 'text/csv'),
    }
    from unittest.mock import mock_open
    m = mock_open()
    with patch("core.web.routes.api.shutil.copyfileobj"), \
         patch("core.web.routes.api.os.makedirs"), \
         patch("core.web.routes.api.open", m, create=True):
        response = client.post("/api/upload", files=files)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

def test_api_config(mock_auth):
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", MagicMock()) as mock_file, \
         patch("yaml.safe_load", return_value={"tables": {"users": {}, "orders": {}}}):
        response = client.get("/api/config")
        assert response.status_code == 200
        assert response.json() == {"tables": ["users", "orders"]}

def test_api_reports(mock_auth):
    with patch("os.path.exists", return_value=True), \
         patch("os.listdir", return_value=["2024-01-01_120000_rep1", "2024-01-02_120000_rep2"]), \
         patch("os.path.isdir", return_value=True):
        response = client.get("/api/reports")
        assert response.status_code == 200
        reports = response.json()["reports"]
        assert len(reports) == 2
        # sorted reverse chronologically
        assert reports[0]["id"] == "2024-01-02_120000_rep2"

@patch("core.web.routes.api.AUDIT_STATE", {"status": "idle", "results_summary": {}, "results_details": []})
def test_api_audit_start(mock_auth):
    response = client.post("/api/audit/start", json={"tables": ["users"]})
    assert response.status_code == 200
    assert response.json()["status"] == "started"

@patch("core.web.routes.api.AUDIT_STATE", {"status": "running", "results_summary": {}, "results_details": []})
def test_api_audit_start_already_running(mock_auth):
    response = client.post("/api/audit/start", json={"tables": ["users"]})
    assert response.status_code == 409

@patch("core.web.routes.api.AUDIT_STATE", {"status": "completed", "results_summary": {"pass": 1}, "results_details": []})
def test_api_audit_results(mock_auth):
    response = client.get("/api/audit/results")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["summary"] == {"pass": 1}

def test_api_download_not_found(mock_auth):
    with patch("os.path.exists", return_value=False):
        response = client.get("/api/reports/123/download?file=test.csv")
        assert response.status_code == 404

import tempfile

def test_api_download_non_csv(mock_auth):
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "123"), exist_ok=True)
        pdf_path = os.path.join(tmpdir, "123", "test.pdf")
        with open(pdf_path, "w") as f:
            f.write("dummy pdf")
            
        with patch("core.web.routes.api.os.path.join", return_value=pdf_path):
            response = client.get("/api/reports/123/download?file=test.pdf")
            assert response.status_code == 200
            assert response.content == b"dummy pdf"


# ─── TST-02: Additional API coverage ──────────────────────────────────────────

def test_api_stream_unauthorized(unauth_mock):
    """GET /api/stream should return 401 when not authenticated."""
    response = client.get("/api/stream")
    assert response.status_code == 401


def test_api_stream_authorized(mock_auth):
    """GET /api/stream should return a streaming response with SSE content."""
    # Mock event_generator to avoid infinite loop during tests
    async def mock_generator():
        yield "data: {\"status\": \"idle\"}\n\n"

    with patch("core.web.routes.api.event_generator", side_effect=mock_generator):
        # We need to be careful with StreamingResponse in TestClient
        # Instead, let's just mock the response for this unit test if it's too risky,
        # or use a timeout.
        response = client.get("/api/stream")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")



def test_api_config_no_file(mock_auth):
    """GET /api/config with no config file should return empty tables list."""
    with patch("core.web.routes.api.os.path.exists", return_value=False):
        response = client.get("/api/config")
        assert response.status_code == 200
        assert response.json() == {"tables": []}


def test_api_upload_no_files(mock_auth):
    """POST /api/upload with no files should still return 200 ok."""
    response = client.post("/api/upload")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["uploaded"]["config"] is None
    assert data["uploaded"]["data_files"] == []


def test_api_download_csv_sanitized(mock_auth):
    """GET /api/reports/{id}/download for a CSV should stream a sanitized version."""
    import pandas as pd
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "results.csv")
        pd.DataFrame({"id": [1, 2], "email": ["a@b.com", "c@d.com"], "amount": [10.0, 20.0]}).to_csv(csv_path, index=False)

        with patch("core.web.routes.api.os.path.exists", return_value=True), \
             patch("core.web.routes.api.os.path.join", return_value=csv_path):
            response = client.get("/api/reports/abc/download?file=results.csv")
            assert response.status_code == 200
            # Email should be hashed (not plain text)
            content = response.content.decode()
            assert "a@b.com" not in content


def test_api_reports_empty(mock_auth):
    """GET /api/reports should return empty list when output dir doesn't exist."""
    with patch("core.web.routes.api.os.path.exists", return_value=False):
        response = client.get("/api/reports")
        assert response.status_code == 200
        assert response.json() == {"reports": []}


def test_api_audit_results_unauthorized(unauth_mock):
    """GET /api/audit/results should return 401 when not authenticated."""
    response = client.get("/api/audit/results")
    assert response.status_code == 401


def test_api_config_unauthorized(unauth_mock):
    """GET /api/config should return 401 when not authenticated."""
    response = client.get("/api/config")
    assert response.status_code == 401


def test_api_reports_unauthorized(unauth_mock):
    """GET /api/reports should return 401 when not authenticated."""
    response = client.get("/api/reports")
    assert response.status_code == 401

