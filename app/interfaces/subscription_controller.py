import asyncio
import csv
from io import StringIO
from typing import List
from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.application.commands import BulkUpdateSubscriptionsCommand, UpdateSubscriptionCommand
from app.application.queries import GetSubscriptionsQuery
from app.application.query_bus import query_bus
from app.infrastructure.database import SessionLocal, get_db
from app.application.handlers import command_bus
from app.infrastructure.models import BulkSubscriptionResponse, NotificationSubscription, SubscriptionResponse


router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_model=List[SubscriptionResponse])
def list_subscriptions(user_id: int = Query(..., description="User ID for subscription preferences")):
    query = GetSubscriptionsQuery(user_id=user_id)
    return query_bus.handle(query)

@router.put("/", response_model=SubscriptionResponse)
def update_subscription(user_id: int, alert_type: str, is_subscribed: bool):
    command = UpdateSubscriptionCommand(user_id=user_id, alert_type=alert_type, is_subscribed=is_subscribed)
    try:
        return command_bus.handle(command)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.put("/bulk", response_model=List[BulkSubscriptionResponse])
def bulk_update_subscriptions(command: BulkUpdateSubscriptionsCommand):
    try:
        return command_bus.handle(command)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))