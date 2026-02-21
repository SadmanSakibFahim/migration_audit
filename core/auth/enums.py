from enum import Enum


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    AUDITOR = "AUDITOR"
    VIEWER = "VIEWER"


class SubscriberType(str, Enum):
    PERSONAL = "PERSONAL"
    ENTERPRISE = "ENTERPRISE"
