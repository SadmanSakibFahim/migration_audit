from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SqEnum
from sqlalchemy.orm import declarative_base, relationship
from core.auth.enums import UserRole, SubscriberType

Base = declarative_base()

class License(Base):
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key_hash = Column(String, unique=True, nullable=False)
    plan_tier = Column(String, default="basic")
    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)

    # Relationships
    subscribers = relationship("Subscriber", back_populates="license", cascade="all, delete-orphan")

class Subscriber(Base):
    __tablename__ = "subscribers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(SqEnum(SubscriberType), nullable=False)
    license_key_id = Column(Integer, ForeignKey("licenses.id"), nullable=False)
    is_active = Column(Boolean, default=True)

    # Relationships
    license = relationship("License", back_populates="subscribers")
    users = relationship("User", back_populates="subscriber")
    enterprise = relationship("Enterprise", back_populates="subscriber", uselist=False)

class Enterprise(Base):
    __tablename__ = "enterprises"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    subscriber_id = Column(Integer, ForeignKey("subscribers.id"), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    subscriber = relationship("Subscriber", back_populates="enterprise")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(SqEnum(UserRole), default=UserRole.VIEWER)
    subscriber_id = Column(Integer, ForeignKey("subscribers.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    subscriber = relationship("Subscriber", back_populates="users")
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")

class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key_hash = Column(String, unique=True, nullable=False)
    prefix = Column(String, nullable=False)  # e.g. "sk_live_"
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="api_keys")
