from sqlalchemy.orm import Session
from app.infrastructure.models import User, Voter

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
    
    def get_all_voters(self):
        return (
            self.db.query(User, Voter)
            .join(Voter, User.id == Voter.user_id)
            .filter(User.role == "voter")
            .all()
        )
    
    def voter_exists(self, voter_id: int) -> bool:
        return (
            self.db.query(User)
            .filter(User.id == voter_id, User.role == "voter")
            .first() is not None
        )
    
    def add_voter(self, voter_id: int, name: str):
        new_voter = Voter(id=voter_id, name=name, has_voted=False)
        self.db.add(new_voter)
        self.db.commit()
        self.db.refresh(new_voter)
        return new_voter
    
    def get_voter_by_user_id(self, user_id: int):
        return self.db.query(Voter).filter(Voter.user_id == user_id).first()
