from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base: Any = declarative_base()

class AuditLogEvent(Base):  # type: ignore[misc]
    """
    Immutable tracking table representing core actions throughout the pipeline.
    """
    __tablename__ = "audit_log_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(100), nullable=False)
    user_id = Column(String, nullable=False)
    ip_address = Column(String(50), nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
