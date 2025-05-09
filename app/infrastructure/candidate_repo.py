from sqlalchemy.orm import Session

class CandidateRepository:
    def __init__(self, db: Session):
        self.db = db