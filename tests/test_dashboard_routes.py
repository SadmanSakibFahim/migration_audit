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
@patch("subprocess.run")
def test_run_audit_authorized(mock_subprocess, mock_log, mock_template, mock_auth):
    mock_template.return_value = "mock_template_response"
    response = client.post("/run-audit")
    assert response.status_code == 200
    mock_template.assert_called_once()
    assert mock_log.called

@patch("core.web.routes.dashboard.get_current_user")
def test_dashboard_no_config(mock_user):
    mock_user.return_value = {"username": "admin", "role": "admin"}
    # os.path.exists returns False by default for our mocked paths unless patched
    with patch("os.path.exists", return_value=False):
        response = client.get("/dashboard")
        assert response.status_code == 200

