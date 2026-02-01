import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.auth.models import Base, User, Enterprise, Subscriber, License, ApiKey
from core.auth.enums import UserRole, SubscriberType

@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_create_license(session):
    lic = License(
        key_hash="hash123",
        valid_from=datetime.utcnow(),
        valid_until=datetime.utcnow() + timedelta(days=365)
    )
    session.add(lic)
    session.commit()
    
    assert lic.id is not None
    assert lic.is_active is True

def test_create_personal_subscriber(session):
    # Setup License
    lic = License(
        key_hash="hash_personal",
        valid_from=datetime.utcnow(),
        valid_until=datetime.utcnow() + timedelta(days=30)
    )
    session.add(lic)
    session.commit()
    
    # Create Subscriber
    sub = Subscriber(
        type=SubscriberType.PERSONAL,
        license_key_id=lic.id
    )
    session.add(sub)
    session.commit()
    
    # Create User linked to Subscriber
    user = User(
        username="jane_doe",
        password_hash="secret",
        role=UserRole.AUDITOR,
        subscriber_id=sub.id
    )
    session.add(user)
    session.commit()
    
    assert user.subscriber.type == SubscriberType.PERSONAL
    assert user.subscriber.license.key_hash == "hash_personal"

def test_create_enterprise_subscriber(session):
    # Setup License
    lic = License(
        key_hash="hash_corp",
        valid_from=datetime.utcnow(),
        valid_until=datetime.utcnow() + timedelta(days=365)
    )
    session.add(lic)
    session.commit()
    
    # Create Subscriber
    sub = Subscriber(
        type=SubscriberType.ENTERPRISE,
        license_key_id=lic.id
    )
    session.add(sub)
    session.commit()
    
    # Create Enterprise Profile
    ent = Enterprise(
        name="Acme Corp",
        subscriber_id=sub.id
    )
    session.add(ent)
    session.commit()
    
    # Create User linked to Subscriber
    user = User(
        username="admin@acme.com",
        password_hash="secret",
        role=UserRole.ADMIN,
        subscriber_id=sub.id
    )
    session.add(user)
    session.commit()
    
    assert user.subscriber.enterprise.name == "Acme Corp"
    assert ent.subscriber.license.plan_tier == "basic"

def test_api_key_relationship(session):
    # Setup Hierarchy
    lic = License(key_hash="k", valid_from=datetime.utcnow(), valid_until=datetime.utcnow())
    session.add(lic)
    session.commit()
    
    sub = Subscriber(type=SubscriberType.PERSONAL, license_key_id=lic.id)
    session.add(sub)
    session.commit()
    
    user = User(username="dev", password_hash="pw", subscriber_id=sub.id)
    session.add(user)
    session.commit()
    
    # Create API Key
    key = ApiKey(
        user_id=user.id,
        key_hash="hashed_key",
        prefix="sk_live_"
    )
    session.add(key)
    session.commit()
    
    assert len(user.api_keys) == 1
    assert user.api_keys[0].prefix == "sk_live_"
