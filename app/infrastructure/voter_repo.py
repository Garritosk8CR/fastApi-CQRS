from sqlalchemy.orm import Session
from app.infrastructure.models import Voter

class VoterRepository:
    def __init__(self, db: Session):
        self.db = db

    def register_voter(self, voter: Voter):
        self.db.add(voter)
        self.db.commit()
        self.db.refresh(voter)
        return voter

    def get_voter_by_id(self, voter_id: int):
        return self.db.query(Voter).filter(Voter.id == voter_id).first()
