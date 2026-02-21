from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.auth.enums import UserRole
from core.auth.models import Base
from core.auth.service import AuthService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_password_hashing(db_session):
    auth = AuthService(db_session)
    pw = "secret123"
    hashed = auth.hash_password(pw)
    assert hashed != pw
    assert auth.verify_password(pw, hashed) is True
    assert auth.verify_password("wrong", hashed) is False


def test_auth_user_flow(db_session):
    auth = AuthService(db_session)

    # Setup License & Sub
    lic = auth.create_license(
        "hash_key", datetime.now(), datetime.now() + timedelta(days=365)
    )
    sub = auth.create_personal_subscriber(lic.id)

    # Create User
    user = auth.create_user("alice", "mypassword", sub.id, UserRole.ADMIN)

    # Authenticate Success
    authenticated_user = auth.authenticate_user("alice", "mypassword")
    assert authenticated_user is not None
    assert authenticated_user.id == user.id

    # Authenticate Fail
    assert auth.authenticate_user("alice", "wrongpass") is None
    assert auth.authenticate_user("bob", "mypassword") is None


def test_license_expiry_check(db_session):
    auth = AuthService(db_session)

    # Valid License
    lic_valid = auth.create_license(
        "valid", datetime.now() - timedelta(days=1), datetime.now() + timedelta(days=1)
    )
    sub_valid = auth.create_personal_subscriber(lic_valid.id)
    user_valid = auth.create_user("u1", "p", sub_valid.id)

    assert auth.is_license_valid(lic_valid) is True
    assert auth.check_access(user_valid) is True

    # Expired License
    lic_expired = auth.create_license(
        "expired",
        datetime.now() - timedelta(days=10),
        datetime.now() - timedelta(days=1),
    )
    sub_expired = auth.create_personal_subscriber(lic_expired.id)
    user_expired = auth.create_user("u2", "p", sub_expired.id)

    assert auth.is_license_valid(lic_expired) is False
    assert auth.check_access(user_expired) is False


def test_rbac_permissions(db_session):
    auth = AuthService(db_session)

    # Setup valid environment
    lic = auth.create_license(
        "rbac_key", datetime.now(), datetime.now() + timedelta(days=365)
    )
    sub = auth.create_personal_subscriber(lic.id)

    admin = auth.create_user("admin", "p", sub.id, UserRole.ADMIN)
    auditor = auth.create_user("auditor", "p", sub.id, UserRole.AUDITOR)
    viewer = auth.create_user("viewer", "p", sub.id, UserRole.VIEWER)

    # Check Admin
    assert auth.check_permission(admin, "run_audit") is True
    assert auth.check_permission(admin, "view_report") is True
    assert auth.check_permission(admin, "delete_user") is True  # Admin can do anything

    # Check Auditor
    assert auth.check_permission(auditor, "run_audit") is True
    assert auth.check_permission(auditor, "view_report") is True
    assert auth.check_permission(auditor, "delete_user") is False

    # Check Viewer
    assert auth.check_permission(viewer, "run_audit") is False
    assert auth.check_permission(viewer, "view_report") is True
    assert auth.check_permission(viewer, "delete_user") is False
