from sqlalchemy.orm import Session
from app.infrastructure.models import AuditLog

class AuditLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_audit_log(self, election_id: int, performed_by: int, action: str, details: str = None):
        audit_log = AuditLog(
            election_id=election_id,
            performed_by=performed_by,
            action=action,
            details=details
        )
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        return audit_log

    def get_audit_logs_by_election(self, election_id: int):
        return self.db.query(AuditLog).filter(AuditLog.election_id == election_id).order_by(AuditLog.timestamp.desc()).all()