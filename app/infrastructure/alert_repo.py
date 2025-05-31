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