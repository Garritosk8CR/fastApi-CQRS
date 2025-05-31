from datetime import datetime, timezone
import math
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.infrastructure.models import Election, Vote, Voter, Alert

class AlertRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_alerts(self, election_id: int = None) -> list:
        query = self.db.query(Alert)
        if election_id:
            query = query.filter(Alert.election_id == election_id)
        alerts = query.all()
        return [
            {
                "id": alert.id,
                "election_id": alert.election_id,
                "alert_type": alert.alert_type,
                "message": alert.message,
                "status": alert.status,
                "created_at": alert.created_at.isoformat(),
            }
            for alert in alerts
        ]
    
    def create_alert(self, election_id: int, alert_type: str, message: str) -> dict:
        alert = Alert(
            election_id=election_id,
            alert_type=alert_type,
            message=message,
            status="new",
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return {
            "id": alert.id,
            "election_id": alert.election_id,
            "alert_type": alert.alert_type,
            "message": alert.message,
            "status": alert.status,
            "created_at": alert.created_at.isoformat(),
        }