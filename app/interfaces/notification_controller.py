import asyncio
import csv
from io import StringIO
from typing import List
from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.application.commands import MarkAllNotificationsReadCommand, MarkNotificationReadCommand
from app.application.queries import GetNotificationsQuery, GetNotificationsSummaryQuery
from app.application.query_bus import query_bus
from app.infrastructure.database import SessionLocal, get_db
from app.application.handlers import command_bus
from app.infrastructure.models import Notification, NotificationResponse


router = APIRouter(prefix="/notifications", tags=["Notifications"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_model=List[NotificationResponse])
def list_notifications(user_id: int = Query(..., description="User ID to fetch notifications for")):
    query = GetNotificationsQuery(user_id=user_id)
    return query_bus.handle(query)

@router.put("/{notification_id}", response_model=NotificationResponse)
def mark_notification_as_read(notification_id: int):
    command = MarkNotificationReadCommand(notification_id=notification_id)
    try:
        return command_bus.handle(command)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.get("/summary")
def notifications_summary(user_id: int = Query(..., description="User ID for summary")):
    query = GetNotificationsSummaryQuery(user_id=user_id)
    return query_bus.handle(query)

@router.put("/mark_all_read/{user_id}")
def mark_all_notifications_as_read(user_id: int):
    print(f"Marking all notifications as read for user ID: {user_id}")
    command = MarkAllNotificationsReadCommand(user_id=user_id)
    return command_bus.handle(command)