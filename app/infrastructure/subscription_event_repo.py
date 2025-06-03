import math
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.infrastructure.models import SubscriptionEvent

class SubscriptionEventRepository:
    def __init__(self, db: Session):
        self.db = db

    def log_event(self, user_id: int, alert_type: str, old_value: bool, new_value: bool) -> SubscriptionEvent:
        event = SubscriptionEvent(
            user_id=user_id,
            alert_type=alert_type,
            old_value=old_value,
            new_value=new_value
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event