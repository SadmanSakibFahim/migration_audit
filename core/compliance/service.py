import csv
import io
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from core.compliance.models import AuditLogEvent


class ComplianceService:
    def __init__(self, session: Session):
        self.session = session

    def log_event(
        self,
        event_type: str,
        user_id: str,
        ip_address: str,
        details: Optional[str] = None
    ) -> AuditLogEvent:
        """
        Records an immutable audit event into the database.
        """
        event = AuditLogEvent(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            details=details,
            timestamp=datetime.utcnow()
        )
        self.session.add(event)
        self.session.commit()
        return event

    def purge_expired_logs(self, retention_days: int = 30) -> int:
        """
        Enforces data retention policies by permanently deleting logs older than X days.
        Returns the number of rows purged.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        deleted_count = self.session.query(AuditLogEvent).filter(
            AuditLogEvent.timestamp < cutoff_date
        ).delete()
        
        self.session.commit()
        return deleted_count

    def export_audit_log_csv(self) -> str:
        """
        Generates a regulatory CSV report containing the entire immutable audit trail.
        """
        events: List[AuditLogEvent] = self.session.query(AuditLogEvent).order_by(AuditLogEvent.timestamp.desc()).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(["ID", "Timestamp", "Event Type", "User ID", "IP Address", "Details"])
        for event in events:
            writer.writerow([
                event.id,
                event.timestamp.isoformat(),
                event.event_type,
                event.user_id,
                event.ip_address,
                event.details or ""
            ])
            
        return output.getvalue()
