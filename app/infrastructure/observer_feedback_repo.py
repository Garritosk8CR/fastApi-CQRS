from sqlalchemy.orm import Session

class ObserverFeedbackRepository:
    def __init__(self, db: Session):
        self.db = db