from datetime import datetime, timezone
import math
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.infrastructure.models import Notification


class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db