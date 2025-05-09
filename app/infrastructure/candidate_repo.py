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
    
    def get_candidates_by_election(self, election_id: int):
        return self.db.query(Candidate).filter(Candidate.election_id == election_id).all()
    
    def update_candidate(self, candidate_id: int, name: str = None, party: str = None, bio: str = None):
        candidate = self.db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            return None

        if name:
            candidate.name = name
        if party:
            candidate.party = party
        if bio:
            candidate.bio = bio

        self.db.commit()
        return candidate