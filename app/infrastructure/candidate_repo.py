from sqlalchemy.orm import Session

from app.infrastructure.models import Candidate

class CandidateRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_candidate(self, name: str, party: str, bio: str, election_id: int):
        candidate = Candidate(name=name, party=party, bio=bio, election_id=election_id)
        self.db.add(candidate)
        self.db.commit()
        self.db.refresh(candidate)
        return candidate