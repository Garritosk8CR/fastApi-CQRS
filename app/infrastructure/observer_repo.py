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
    
    def create_observer(self,observer: Observer):
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
    
    def update_observer(self,p_observer: Observer):
        observer = self.db.query(Observer).filter(Observer.id == p_observer.observer_id).first()
        if not observer:
            return None

        if p_observer.name:
            observer.name = p_observer.name
        if p_observer.email:
            observer.email = p_observer.email
        if p_observer.organization:
            observer.organization = p_observer.organization

        self.db.commit()
        return observer