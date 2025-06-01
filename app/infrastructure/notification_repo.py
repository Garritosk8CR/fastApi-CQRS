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
    
    def create_notification(self, alert_id: int, user_id: int, message: str) -> dict:
        notification = Notification(
            alert_id=alert_id,
            user_id=user_id,
            message=message,
            is_read=False,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return {
            "id": notification.id,
            "alert_id": notification.alert_id,
            "user_id": notification.user_id,
            "message": notification.message,
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat(),
        }
    
    # New method: Get a summary for a user—both total and unread counts.
    def get_notifications_summary(self, user_id: int) -> dict:
        total = self.db.query(Notification).filter(Notification.user_id == user_id).count()
        unread = self.db.query(Notification).filter(Notification.user_id == user_id, Notification.is_read == False).count()
        return {"total": total, "unread": unread}
    
    # New method: Mark all notifications as read for a given user.
    def mark_all_notifications_as_read(self, user_id: int) -> dict:
        notifications = self.db.query(Notification).filter(Notification.user_id == user_id, Notification.is_read == False).all()
        count = 0
        for n in notifications:
            n.is_read = True
            count += 1
        self.db.commit()
        return {"marked_read": count}