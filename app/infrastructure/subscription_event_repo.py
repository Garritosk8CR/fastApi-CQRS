import math
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.infrastructure.models import SubscriptionEvent

class SubscriptionEventRepository:
    def __init__(self, db: Session):
        self.db = db