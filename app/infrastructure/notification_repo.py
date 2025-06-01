from datetime import datetime, timezone
import math
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.infrastructure.models import Notification


class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_notifications(self, user_id: int) -> list:
        notifications = (
            self.db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .all()
        )
        return [
            {
                "id": n.id,
                "alert_id": n.alert_id,
                "user_id": n.user_id,
                "message": n.message,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifications
        ]
    
    def mark_notification_as_read(self, notification_id: int) -> dict:
        n = self.db.query(Notification).filter(Notification.id == notification_id).first()
        if not n:
            raise Exception("Notification not found")
        n.is_read = True
        self.db.commit()
        self.db.refresh(n)
        return {
            "id": n.id,
            "alert_id": n.alert_id,
            "user_id": n.user_id,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat(),
        }