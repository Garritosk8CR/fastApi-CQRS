from sqlalchemy.orm import Session
from app.infrastructure.models import Observer

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