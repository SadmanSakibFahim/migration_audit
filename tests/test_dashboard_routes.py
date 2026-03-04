import os
# Note: SECRET_KEY, AUTH_DB_URI, ALLOWED_HOSTS are set globally in conftest.py

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from core.web.app import app

client = TestClient(app)

@pytest.fixture
def mock_auth():
    with patch("core.web.routes.dashboard.get_current_user") as mock_user:
        mock_user.return_value = {"username": "admin", "role": "admin", "id": 1}
        yield mock_user

@pytest.fixture
def unauth_mock():
    with patch("core.web.routes.dashboard.get_current_user") as mock_user:
        mock_user.return_value = None
        yield mock_user

@patch("core.web.routes.dashboard.templates.TemplateResponse")
def test_dashboard_unauthorized(mock_template, unauth_mock):
    response = client.get("/dashboard")
    # Redirects to /login
    assert response.url.path == "/login" # httpx follows redirects by default? No, TestClient does follow if allow_redirects=True. TestClient default is Follow.
    # Actually let's just use allow_redirects=False
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code in [302, 303, 307]
    assert response.headers["location"] == "/login"

@patch("core.web.routes.dashboard.templates.TemplateResponse")
@patch("core.audit.logger.log_audit_event")
def test_dashboard_authorized(mock_log, mock_template, mock_auth):
    mock_template.return_value = "mock_template_response"
    
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", MagicMock()), \
         patch("yaml.safe_load", return_value={"tables": {"A": 1}}), \
         patch("os.listdir", return_value=["rep1"]), \
         patch("os.path.isdir", return_value=True):
         
        response = client.get("/dashboard")
        assert response.status_code == 200
        mock_template.assert_called_once()
        assert mock_log.called

@patch("core.web.routes.dashboard.templates.TemplateResponse")
def test_run_audit_unauthorized(mock_template, unauth_mock):
    response = client.post("/run-audit", follow_redirects=False)
    assert response.status_code in [302, 303, 307]
    assert response.headers["location"] == "/login"

@patch("core.web.routes.dashboard.templates.TemplateResponse")
@patch("core.audit.logger.log_audit_event")
def test_run_audit_authorized(mock_log, mock_template, mock_auth):
    mock_template.return_value = "mock_template_response"
    response = client.post("/run-audit")
    assert response.status_code == 200
    mock_template.assert_called_once()
    assert mock_log.called


@patch("core.web.routes.api.get_current_user")
def test_api_upload_rbac_enforced(mock_user):
    # user fixture returns viewer (no run_audit permission)
    mock_user.return_value = {"username": "viewer", "role": "viewer", "id": 3}
    response = client.post("/api/upload", files={})
    assert response.status_code == 403 or response.status_code == 401


@patch("core.web.routes.api.get_current_user")
def test_api_upload_allowed_for_auditor(mock_user):
    mock_user.return_value = {"username": "auditor", "role": "auditor", "id": 2}
    # we also need a dummy db session so decorator doesn't crash
    from core.web.routes.auth import SessionLocal
    def attach_db(request, call_next):
        request.state.db = SessionLocal()
        return call_next(request)

    # simple call: it will hit permission decorator but no actual file processing
    response = client.post("/api/upload", files={})
    # since there is no config/data sent, endpoint returns ok or empty but must not be 403
    assert response.status_code in [200, 422]
