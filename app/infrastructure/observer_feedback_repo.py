from collections import defaultdict
import csv
import io
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.infrastructure.models import ObserverFeedback
from textblob import TextBlob

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
    
    def get_time_patterns(self):
        time_data = self.db.query(func.date(ObserverFeedback.timestamp), func.count(ObserverFeedback.id)) \
                           .group_by(func.date(ObserverFeedback.timestamp)) \
                           .order_by(func.date(ObserverFeedback.timestamp)).all()

        patterns = [{"date": date.isoformat(), "report_count": count} for date, count in time_data]

        return patterns
    
    def analyze_sentiment(self):
        feedbacks = self.db.query(ObserverFeedback.id, ObserverFeedback.description).all()

        sentiments = []
        for feedback in feedbacks:
            sentiment_score = TextBlob(feedback.description).sentiment.polarity
            sentiment_category = "Positive" if sentiment_score > 0.2 else "Neutral" if -0.2 <= sentiment_score <= 0.2 else "Negative"

            sentiments.append({
                "feedback_id": feedback.id,
                "description": feedback.description,
                "sentiment": sentiment_category,
                "score": round(sentiment_score, 2)
            })

        return sentiments
    
    def export_observer_feedback(self, export_format: str = "json"):
        feedbacks = self.db.query(ObserverFeedback).all()
        
        if export_format.lower() == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            # Write CSV header including election_id
            writer.writerow(["id", "observer_id", "election_id", "description", "severity", "timestamp"])
            # Write feedback data rows including the election_id field
            for fb in feedbacks:
                writer.writerow([
                    fb.id,
                    fb.observer_id,
                    fb.election_id,  # Added election_id here
                    fb.description,
                    fb.severity,
                    fb.timestamp.isoformat() if fb.timestamp else ""
                ])
            csv_data = output.getvalue()
            output.close()
            return csv_data
        
        # Default JSON export: return list of dictionaries with election_id
        return [
            {
                "id": fb.id,
                "observer_id": fb.observer_id,
                "election_id": fb.election_id,  # Added election_id here
                "description": fb.description,
                "severity": fb.severity,
                "timestamp": fb.timestamp.isoformat() if fb.timestamp else None,
            } for fb in feedbacks
        ]
    
    def get_feedback_category_analytics(self, election_id: int):
        # Retrieve all feedback for the specified election.
        feedbacks = self.db.query(ObserverFeedback).filter(ObserverFeedback.election_id == election_id).all()
        
        # Define a mapping of categories to keywords.
        categories_map = {
            "Security": ["security", "fraud", "attack", "unauthorized", "cheat"],
            "Operational": ["delay", "waiting", "staff", "line", "issue", "administration"],
            "Technical": ["error", "bug", "system", "technical", "software", "hardware"],
        }
        
        # Use a defaultdict to count occurrences.
        category_counts = defaultdict(int)
        
        for fb in feedbacks:
            desc = fb.description.lower() if fb.description else ""
            found_category = None
            # Attempt to match a category based on keywords.
            for category, keywords in categories_map.items():
                for keyword in keywords:
                    if keyword in desc:
                        found_category = category
                        break
                if found_category is not None:
                    break
            # If no category matches, classify as "Other"
            if found_category is None:
                found_category = "Other"
            category_counts[found_category] += 1
        
        # Convert counts to a list of dictionaries.
        result = [{"category": cat, "count": count} for cat, count in category_counts.items()]
        return result