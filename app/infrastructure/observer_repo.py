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