import math
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.infrastructure.models import NotificationSubscription


class SubscriptionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_subscriptions(self, user_id: int) -> list:
        subscriptions = self.db.query(NotificationSubscription).filter(
            NotificationSubscription.user_id == user_id
        ).all()
        return [
            {
                "id": s.id,
                "user_id": s.user_id,
                "alert_type": s.alert_type,
                "is_subscribed": s.is_subscribed,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in subscriptions
        ]