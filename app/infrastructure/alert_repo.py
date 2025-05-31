import math
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.infrastructure.models import Election, Vote, Voter, Alert

class AlertRepository:
    def __init__(self, db: Session):
        self.db = db