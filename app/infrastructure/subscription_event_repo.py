import math
from sqlalchemy import case, func
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
    
    def get_subscription_analytics(self, user_id: int) -> list:
        query = self.db.query(
            SubscriptionEvent.alert_type,
            func.count(SubscriptionEvent.id).label("total_changes"),
            func.sum(case([(SubscriptionEvent.new_value == True, 1)], else_=0)).label("enabled_count"),
            func.sum(case([(SubscriptionEvent.new_value == False, 1)], else_=0)).label("disabled_count")
        ).filter(SubscriptionEvent.user_id == user_id).group_by(SubscriptionEvent.alert_type)
        results = query.all()
        return [
            {
                "alert_type": row[0],
                "total_changes": row[1],
                "enabled_count": row[2],
                "disabled_count": row[3]
            }
            for row in results
        ]