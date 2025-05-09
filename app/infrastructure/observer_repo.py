from sqlalchemy.orm import Session
from app.infrastructure.models import Observer

class ObserverRepository:
    def __init__(self, db: Session):
        self.db = db