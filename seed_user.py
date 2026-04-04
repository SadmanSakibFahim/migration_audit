from albatross_pro.web.routes.auth import SessionLocal, provision_schemas
from albatross_pro.auth.service import AuthService
from albatross_pro.auth.enums import UserRole, SubscriberType, PlanTier
from albatross_pro.auth.models import User, Enterprise, Subscriber, License
from datetime import datetime, timedelta
import hashlib
import time

def seed():
    provision_schemas()
    db = SessionLocal()
    auth = AuthService(db)
    
    # Check if user exists
    if db.query(User).filter_by(username="mega_admin").first():
        print("User mega_admin already exists")
        return

    # Create license
    key_hash = hashlib.sha256("test_license".encode()).hexdigest()
    lic = auth.create_license(
        key_hash=key_hash, 
        valid_from=datetime.now(), 
        valid_until=datetime.now() + timedelta(days=365), 
        plan="enterprise"
    )
    
    # Create subscriber
    # In auth.py, create_enterprise_subscriber seems to be a method of AuthService
    # Let's check AuthService methods in albatross_pro/auth/service.py
    # For now, I'll just use the models directly if I can't find the service method
    
    sub = Subscriber(type=SubscriberType.ENTERPRISE, license_key_id=lic.id)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    
    ent = Enterprise(name="MegaOrg", subscriber_id=sub.id)
    db.add(ent)
    db.commit()
    
    # Create user
    user = auth.create_user(
        username="mega_admin",
        password="secure_pass",
        subscriber_id=sub.id,
        role=UserRole.ADMIN
    )
    print("User mega_admin seeded")
    db.close()

if __name__ == "__main__":
    seed()
