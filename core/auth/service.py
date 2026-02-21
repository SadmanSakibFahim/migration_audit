from datetime import datetime

from passlib.hash import argon2
from sqlalchemy.orm import Session

from core.auth.enums import SubscriberType, UserRole
from core.auth.models import Enterprise, License, Subscriber, User


class AuthService:
    def __init__(self, session: Session):
        self.session = session

    def hash_password(self, password: str) -> str:
        return argon2.using(rounds=4).hash(password)

    def verify_password(self, password: str, hashed: str) -> bool:
        return argon2.verify(password, hashed)

    def create_license(
        self, key_hash: str, valid_from: datetime, valid_until: datetime, plan="basic"
    ) -> License:
        lic = License(
            key_hash=key_hash,
            valid_from=valid_from,
            valid_until=valid_until,
            plan_tier=plan,
            is_active=True,
        )
        self.session.add(lic)
        self.session.commit()
        return lic

    def create_personal_subscriber(self, license_id: int) -> Subscriber:
        sub = Subscriber(
            type=SubscriberType.PERSONAL, license_key_id=license_id, is_active=True
        )
        self.session.add(sub)
        self.session.commit()
        return sub

    def create_enterprise_subscriber(self, license_id: int, name: str) -> Subscriber:
        sub = Subscriber(
            type=SubscriberType.ENTERPRISE, license_key_id=license_id, is_active=True
        )
        self.session.add(sub)
        self.session.flush()  # Get ID

        ent = Enterprise(name=name, subscriber_id=sub.id)
        self.session.add(ent)
        self.session.commit()
        return sub

    def create_user(
        self,
        username: str,
        password: str,
        subscriber_id: int,
        role: UserRole = UserRole.VIEWER,
    ) -> User:
        user = User(
            username=username,
            password_hash=self.hash_password(password),
            role=role,
            subscriber_id=subscriber_id,
            is_active=True,
        )
        self.session.add(user)
        self.session.commit()
        return user

    def authenticate_user(self, username: str, password: str) -> User | None:
        user = self.session.query(User).filter_by(username=username).first()
        if not user or not user.is_active:
            return None

        if self.verify_password(password, user.password_hash):
            return user
        return None

    def is_license_valid(self, license_obj: License) -> bool:
        if not license_obj.is_active:
            return False

        now = datetime.now()
        # In case dates are timezone naive, we assume system local or naive UTC
        # If dates in DB are naive UTC, Ensure 'now' is compatible.
        # Here we just compare naive against naive for MVP simplicity
        return license_obj.valid_from <= now <= license_obj.valid_until

    def check_access(self, user: User) -> bool:
        """
        Full check: User active -> Subscriber active -> License valid
        """
        if not user.is_active:
            return False

        sub = user.subscriber
        if not sub.is_active:
            return False

        return self.is_license_valid(sub.license)

    def check_permission(self, user: User, action: str) -> bool:
        """
        Check if user has permission to perform an action based on their role.
        Hierarchy:
        - ADMIN: All actions
        - AUDITOR: run_audit, view_report
        - VIEWER: view_report
        """
        if not self.check_access(user):
            return False

        if user.role == UserRole.ADMIN:
            return True

        if user.role == UserRole.AUDITOR:
            return action in ["run_audit", "view_report"]

        if user.role == UserRole.VIEWER:
            return action in ["view_report"]

        return False
