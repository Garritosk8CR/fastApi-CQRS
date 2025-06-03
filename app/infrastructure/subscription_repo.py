import math
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.infrastructure.models import NotificationSubscription
from app.infrastructure.subscription_event_repo import SubscriptionEventRepository


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
    
    def update_subscription(self, user_id: int, alert_type: str, is_subscribed: bool) -> dict:
        subscription = self.db.query(NotificationSubscription).filter(
            NotificationSubscription.user_id == user_id,
            NotificationSubscription.alert_type == alert_type
        ).first()
        if not subscription:
            # Create a new record if one doesn't exist.
            subscription = NotificationSubscription(
                user_id=user_id,
                alert_type=alert_type,
                is_subscribed=is_subscribed
            )
            self.db.add(subscription)
        else:
            subscription.is_subscribed = is_subscribed
        self.db.commit()
        self.db.refresh(subscription)
        return {
            "id": subscription.id,
            "user_id": subscription.user_id,
            "alert_type": subscription.alert_type,
            "is_subscribed": subscription.is_subscribed,
            "created_at": subscription.created_at.isoformat(),
            "updated_at": subscription.updated_at.isoformat() if subscription.updated_at else None,
        }
    
    def bulk_update_subscriptions(self, user_id: int, updates: list) -> list:
        results = []
        event_repo = SubscriptionEventRepository(self.db)
        for update in updates:
            alert_type = update.get("alert_type")
            is_subscribed = update.get("is_subscribed")
            subscription = (
                self.db.query(NotificationSubscription)
                .filter(
                    NotificationSubscription.user_id == user_id,
                    NotificationSubscription.alert_type == alert_type
                )
                .first()
            )
            old_value = subscription.is_subscribed if subscription else None
            if not subscription:
                subscription = NotificationSubscription(
                    user_id=user_id,
                    alert_type=alert_type,
                    is_subscribed=is_subscribed
                )
                self.db.add(subscription)
            else:
                subscription.is_subscribed = is_subscribed
            results.append(subscription)
            self.db.flush()  # ensures IDs and changes are available
            # Log event if there is a change (even creation is considered a change)
            if old_value is None or old_value != is_subscribed:
                effective_old = old_value if old_value is not None else False
                event_repo.log_event(user_id, alert_type, effective_old, is_subscribed)
        self.db.commit()
        for subscription in results:
            self.db.refresh(subscription)
        return [
            {
                "id": s.id,
                "user_id": s.user_id,
                "alert_type": s.alert_type,
                "is_subscribed": s.is_subscribed,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in results
        ]
    
    def initialize_default_subscriptions(self, user_id: int, default_alert_types: list) -> list:
        results = []
        for alert_type in default_alert_types:
            subscription = NotificationSubscription(
                user_id=user_id,
                alert_type=alert_type,
                is_subscribed=True  # default to subscribed
            )
            self.db.add(subscription)
            results.append(subscription)
        self.db.commit()
        for subscription in results:
            self.db.refresh(subscription)
        return results