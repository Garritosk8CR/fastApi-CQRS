from sqlalchemy.orm import Session
from app.infrastructure.models import ObserverFeedback

class ObserverFeedbackRepository:
    def __init__(self, db: Session):
        self.db = db

    def submit_feedback(self, observer_id: int, election_id: int, description: str, severity: str):
        feedback = ObserverFeedback(
            observer_id=observer_id,
            election_id=election_id,
            description=description,
            severity=severity
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback
    
    def get_feedback_by_election(self, election_id: int):
        return self.db.query(ObserverFeedback).filter(ObserverFeedback.election_id == election_id).all()
    
    def get_feedback_by_severity(self, severity: str):
        return self.db.query(ObserverFeedback).filter(ObserverFeedback.severity == severity).all()