import asyncio
import csv
from io import StringIO
from typing import List
from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.application.commands import MarkAllNotificationsReadCommand, MarkNotificationReadCommand
from app.application.queries import GetNotificationsQuery, GetNotificationsSummaryQuery, GetSubscriptionsQuery
from app.application.query_bus import query_bus
from app.infrastructure.database import SessionLocal, get_db
from app.application.handlers import command_bus
from app.infrastructure.models import NotificationSubscription, SubscriptionResponse


router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_model=List[SubscriptionResponse])
def list_subscriptions(user_id: int = Query(..., description="User ID for subscription preferences")):
    query = GetSubscriptionsQuery(user_id=user_id)
    return query_bus.handle(query)