from sqlalchemy import func
from sqlalchemy.orm import Session
from app.infrastructure.models import Observer, ObserverFeedback

class ObserverRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_observer(self, name: str, email: str, election_id: int, organization: str = None):
        observer = Observer(name=name, email=email, election_id=election_id, organization=organization)
        self.db.add(observer)
        self.db.commit()
        self.db.refresh(observer)
        return observer
    
    
    def get_observers_by_election(self, election_id: int):
        return self.db.query(Observer).filter(Observer.election_id == election_id).all()
    
    def update_observer(self, observer_id: int, name: str = None, email: str = None, organization: str = None):
        observer = self.db.query(Observer).filter(Observer.id == observer_id).first()
        if not observer:
            return None

        if name:
            observer.name = name
        if email:
            observer.email = email
        if organization:
            observer.organization = organization

        self.db.commit()
        return observer
    
    def delete_observer(self, observer_id: int):
        observer = self.db.query(Observer).filter(Observer.id == observer_id).first()
        if observer:
            self.db.delete(observer)
            self.db.commit()
            return True
        return False
    
    def get_observer_by_id(self, observer_id: int):
        return self.db.query(Observer).filter(Observer.id == observer_id).first()
    
    def calculate_observer_trust_scores(self):
        observer_data = self.db.query(Observer.id, func.count(ObserverFeedback.id).label("report_count")) \
                               .join(ObserverFeedback, ObserverFeedback.observer_id == Observer.id) \
                               .group_by(Observer.id) \
                               .all()

        observer_scores = []
        for observer_id, report_count in observer_data:
            trust_score = min(100, report_count * 10)  # Example scoring logic

            observer_scores.append({
                "observer_id": observer_id,
                "report_count": report_count,
                "trust_score": trust_score
            })

        return observer_scores