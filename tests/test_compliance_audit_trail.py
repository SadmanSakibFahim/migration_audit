import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import csv
import io

from core.compliance.models import Base, AuditLogEvent
from core.compliance.service import ComplianceService

# Use an in-memory SQLite DB for isolating compliance integration tests
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    # Setup
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    # Teardown
    db.close()
    Base.metadata.drop_all(bind=engine)

def _seed_events(db, days_ago_list):
    for days_ago in days_ago_list:
        event = AuditLogEvent(
            event_type="TEST_EVENT",
            user_id="test_user",
            ip_address="127.0.0.1",
            details=f"Event from {days_ago} days ago",
            timestamp=datetime.utcnow() - timedelta(days=days_ago)
        )
        db.add(event)
    db.commit()

def test_audit_log_creation(db_session):
    service = ComplianceService(db_session)
    event = service.log_event(
        event_type="LOGIN_SUCCESS",
        user_id="admin@sys",
        ip_address="192.168.1.5",
        details="Tested log insertion"
    )
    
    assert event.id is not None
    assert event.event_type == "LOGIN_SUCCESS"
    assert event.user_id == "admin@sys"
    
    # Verify persistence
    fetched = db_session.query(AuditLogEvent).filter_by(event_type="LOGIN_SUCCESS").first()
    assert fetched is not None
    assert fetched.ip_address == "192.168.1.5"

def test_retention_purge_logic(db_session):
    # Seed events: 1 today, 1 month ago, 1 two months ago
    _seed_events(db_session, [0, 15, 31, 60])
    
    # Should have 4 initially
    assert db_session.query(AuditLogEvent).count() == 4
    
    service = ComplianceService(db_session)
    # Purge older than 30 days
    purged_count = service.purge_expired_logs(retention_days=30)
    
    # Events at 31 and 60 days should be deleted
    assert purged_count == 2
    assert db_session.query(AuditLogEvent).count() == 2
    
def test_export_audit_log_csv(db_session):
    _seed_events(db_session, [1])
    service = ComplianceService(db_session)
    service.log_event("SPECIAL_ACTION", "user_123", "10.0.0.1", "Special Details")
    
    csv_string = service.export_audit_log_csv()
    
    # Basic structural assertions
    assert "ID,Timestamp,Event Type,User ID,IP Address,Details" in csv_string
    assert "TEST_EVENT" in csv_string
    assert "SPECIAL_ACTION" in csv_string
    assert "user_123" in csv_string
    assert "10.0.0.1" in csv_string
    
    # Verify row counts (Header + 2 rows = 3 items split by newline)
    rows = csv_string.strip().split("\r\n")
    assert len(rows) == 3
