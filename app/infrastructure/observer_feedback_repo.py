from sqlalchemy import func
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
    
    def get_integrity_score(self, election_id: int):
        feedbacks = self.db.query(ObserverFeedback).filter(ObserverFeedback.election_id == election_id).all()

        if not feedbacks:
            return {"election_id": election_id, "risk_score": 0, "status": "Stable"}

        severity_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        for feedback in feedbacks:
            severity_counts[feedback.severity] += 1

        total_reports = sum(severity_counts.values())
        risk_score = (severity_counts["HIGH"] * 3 + severity_counts["MEDIUM"] * 2 + severity_counts["LOW"]) / total_reports

        risk_status = "Critical" if risk_score >= 2.5 else "Moderate" if risk_score >= 1.5 else "Stable"

        return {
            "election_id": election_id,
            "risk_score": round(risk_score, 2),
            "status": risk_status,
            "breakdown": severity_counts
        }
    
    def get_severity_distribution(self):
        feedbacks = self.db.query(ObserverFeedback.severity, func.count(ObserverFeedback.id)) \
                           .group_by(ObserverFeedback.severity).all()

        severity_counts = {severity: count for severity, count in feedbacks}

        return {
            "LOW": severity_counts.get("LOW", 0),
            "MEDIUM": severity_counts.get("MEDIUM", 0),
            "HIGH": severity_counts.get("HIGH", 0)
        }
    
    def get_top_observers(self, limit=10):
        observer_reports = self.db.query(ObserverFeedback.observer_id, func.count(ObserverFeedback.id)) \
                                  .group_by(ObserverFeedback.observer_id) \
                                  .order_by(func.count(ObserverFeedback.id).desc()) \
                                  .limit(limit).all()

        rankings = [{"observer_id": observer_id, "report_count": count} for observer_id, count in observer_reports]

        return rankings