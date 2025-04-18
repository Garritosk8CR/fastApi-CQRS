from sqlalchemy.orm import Session
from app.infrastructure.models import Election

class ElectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_election(self, election: Election):
        self.db.add(election)
        self.db.commit()
        self.db.refresh(election)
        return election

    def get_election_by_id(self, election_id: int):
        return self.db.query(Election).filter(Election.id == election_id).first()
