from sqlalchemy.orm import Session

class VoteRepository:
    def __init__(self, db: Session):
        self.db = db