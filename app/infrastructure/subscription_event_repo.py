import math
from sqlalchemy import case, func
from sqlalchemy.orm import Session
from app.infrastructure.models import SubscriptionEvent, User

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
            func.sum(case((SubscriptionEvent.new_value == True, 1), else_=0)).label("enabled_count"),
            func.sum(case((SubscriptionEvent.new_value == False, 1), else_=0)).label("disabled_count")
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
    
    def get_subscription_analytics_time_series(self, user_id: int, group_by: str = "day") -> list:
        # Choose the date_trunc format: "day", "week", or "month"
        if group_by not in ["day", "week", "month"]:
            group_by = "day"
        trunc_func = func.date_trunc(group_by, SubscriptionEvent.created_at)
        
        query = self.db.query(
            trunc_func.label("period"),
            SubscriptionEvent.alert_type,
            func.count(SubscriptionEvent.id).label("total_changes"),
            func.sum(case((SubscriptionEvent.new_value == True, 1), else_=0)).label("enabled_count"),
            func.sum(case((SubscriptionEvent.new_value == False, 1), else_=0)).label("disabled_count")
        ).filter(SubscriptionEvent.user_id == user_id).group_by("period", SubscriptionEvent.alert_type).order_by("period")
        
        results = query.all()
        return [
            {
                "period": row[0].isoformat() if row[0] else None,
                "alert_type": row[1],
                "total_changes": row[2],
                "enabled_count": row[3],
                "disabled_count": row[4]
            }
            for row in results
        ]
    
    def get_subscription_analytics_by_region(self, region: str) -> list:
        # This requires that you have defined a User model with, say, a "region" column.
        
        query = self.db.query(
            User.region,
            SubscriptionEvent.alert_type,
            func.count(SubscriptionEvent.id).label("total_changes"),
            func.sum(case((SubscriptionEvent.new_value == True, 1), else_=0)).label("enabled_count"),
            func.sum(case((SubscriptionEvent.new_value == False, 1), else_=0)).label("disabled_count")
        ).join(User, User.id == SubscriptionEvent.user_id)\
        .filter(User.region == region)\
        .group_by(User.region, SubscriptionEvent.alert_type)
        
        results = query.all()
        return [
            {
                "region": row[0],
                "alert_type": row[1],
                "total_changes": row[2],
                "enabled_count": row[3],
                "disabled_count": row[4]
            }
            for row in results
        ]