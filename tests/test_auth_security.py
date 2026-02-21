"""Auth & Security Tests — April Ludgate (T011)

Tests for authentication edge cases, RBAC enforcement, and security posture.
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.auth.enums import UserRole
from core.auth.models import Base
from core.auth.service import AuthService


@pytest.fixture
def auth_setup():
    """Create a fresh auth environment with all 3 roles."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    auth = AuthService(session)

    lic = auth.create_license(
        "sec_test_key",
        datetime.now() - timedelta(days=1),
        datetime.now() + timedelta(days=365),
    )
    sub = auth.create_personal_subscriber(lic.id)

    admin = auth.create_user("admin", "Admin!Pass123", sub.id, UserRole.ADMIN)
    auditor = auth.create_user("auditor", "Auditor!Pass123", sub.id, UserRole.AUDITOR)
    viewer = auth.create_user("viewer", "Viewer!Pass123", sub.id, UserRole.VIEWER)

    return (
        auth,
        session,
        {"admin": admin, "auditor": auditor, "viewer": viewer, "sub": sub, "lic": lic},
    )


# ===================================================================
# Password Hashing
# ===================================================================


class TestPasswordSecurity:
    def test_same_password_different_hashes(self, auth_setup):
        """Argon2 salting ensures same password → different hashes."""
        auth, _, _ = auth_setup
        h1 = auth.hash_password("identical")
        h2 = auth.hash_password("identical")
        assert h1 != h2  # Salt makes them unique

    def test_empty_password_can_be_hashed(self, auth_setup):
        """Empty password doesn't crash (though business logic should reject it)."""
        auth, _, _ = auth_setup
        h = auth.hash_password("")
        assert auth.verify_password("", h) is True

    def test_long_password_can_be_hashed(self, auth_setup):
        """Very long passwords handled correctly."""
        auth, _, _ = auth_setup
        long_pw = "a" * 1000
        h = auth.hash_password(long_pw)
        assert auth.verify_password(long_pw, h) is True

    def test_unicode_password(self, auth_setup):
        """Unicode passwords work."""
        auth, _, _ = auth_setup
        pw = "密码🔑пароль"
        h = auth.hash_password(pw)
        assert auth.verify_password(pw, h) is True

    def test_wrong_password_fails(self, auth_setup):
        """Incorrect password always rejected."""
        auth, _, _ = auth_setup
        h = auth.hash_password("correct")
        assert auth.verify_password("wrong", h) is False


# ===================================================================
# Authentication
# ===================================================================


class TestAuthentication:
    def test_valid_login(self, auth_setup):
        auth, _, users = auth_setup
        user = auth.authenticate_user("admin", "Admin!Pass123")
        assert user is not None
        assert user.username == "admin"

    def test_wrong_password_rejected(self, auth_setup):
        auth, _, _ = auth_setup
        assert auth.authenticate_user("admin", "WrongPass") is None

    def test_nonexistent_user_rejected(self, auth_setup):
        auth, _, _ = auth_setup
        assert auth.authenticate_user("nonexistent", "anything") is None

    def test_sql_injection_username_safe(self, auth_setup):
        """SQL injection in username field should not bypass auth."""
        auth, _, _ = auth_setup
        assert auth.authenticate_user("' OR 1=1 --", "anything") is None
        assert auth.authenticate_user("admin'--", "anything") is None
        assert auth.authenticate_user("'; DROP TABLE users;--", "anything") is None

    def test_inactive_user_cannot_login(self, auth_setup):
        """Deactivated user should be rejected."""
        auth, session, users = auth_setup
        users["admin"].is_active = False
        session.commit()
        assert auth.authenticate_user("admin", "Admin!Pass123") is None


# ===================================================================
# RBAC — Role-Based Access Control
# ===================================================================


class TestRBAC:
    """Tests the check_permission() role matrix."""

    def test_admin_can_do_everything(self, auth_setup):
        auth, _, users = auth_setup
        for action in ["run_audit", "view_report", "delete_user", "manage_config"]:
            assert auth.check_permission(users["admin"], action) is True

    def test_auditor_can_run_audit(self, auth_setup):
        auth, _, users = auth_setup
        assert auth.check_permission(users["auditor"], "run_audit") is True

    def test_auditor_can_view_report(self, auth_setup):
        auth, _, users = auth_setup
        assert auth.check_permission(users["auditor"], "view_report") is True

    def test_auditor_cannot_delete_user(self, auth_setup):
        auth, _, users = auth_setup
        assert auth.check_permission(users["auditor"], "delete_user") is False

    def test_viewer_can_view_report(self, auth_setup):
        auth, _, users = auth_setup
        assert auth.check_permission(users["viewer"], "view_report") is True

    def test_viewer_cannot_run_audit(self, auth_setup):
        auth, _, users = auth_setup
        assert auth.check_permission(users["viewer"], "run_audit") is False

    def test_viewer_cannot_delete_user(self, auth_setup):
        auth, _, users = auth_setup
        assert auth.check_permission(users["viewer"], "delete_user") is False


# ===================================================================
# License & Access Control
# ===================================================================


class TestLicenseAccess:
    def test_expired_license_blocks_access(self, auth_setup):
        auth, session, users = auth_setup
        # Expire the license
        users["lic"].valid_until = datetime.now() - timedelta(days=1)
        session.commit()
        assert auth.check_access(users["admin"]) is False

    def test_expired_license_blocks_permission(self, auth_setup):
        """Even admin cannot act with expired license."""
        auth, session, users = auth_setup
        users["lic"].valid_until = datetime.now() - timedelta(days=1)
        session.commit()
        assert auth.check_permission(users["admin"], "run_audit") is False

    def test_inactive_license_blocks_access(self, auth_setup):
        auth, session, users = auth_setup
        users["lic"].is_active = False
        session.commit()
        assert auth.check_access(users["admin"]) is False

    def test_inactive_subscriber_blocks_access(self, auth_setup):
        auth, session, users = auth_setup
        users["sub"].is_active = False
        session.commit()
        assert auth.check_access(users["admin"]) is False

    def test_inactive_user_blocks_access(self, auth_setup):
        auth, session, users = auth_setup
        users["admin"].is_active = False
        session.commit()
        assert auth.check_access(users["admin"]) is False
