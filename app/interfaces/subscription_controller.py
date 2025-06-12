import asyncio
import csv
from datetime import datetime
from io import StringIO
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.application.commands import BulkUpdateSubscriptionsCommand, UpdateSubscriptionCommand
from app.application.queries import CorrelationAnalyticsQuery, EnhancedNeuralNetworkPredictiveAnalyticsQuery, EnhancedPredictiveSubscriptionAnalyticsQuery, GetSubscriptionAnalyticsQuery, GetSubscriptionsQuery, PredictiveSubscriptionAnalyticsQuery, SegmentSubscriptionAnalyticsQuery, SubscriptionConversionMetricsQuery, TimeSeriesSubscriptionAnalyticsQuery
from app.application.query_bus import query_bus
from app.infrastructure.database import SessionLocal, get_db
from app.application.handlers import command_bus
from app.infrastructure.models import BulkSubscriptionResponse, NotificationSubscription, SubscriptionResponse
from app.interfaces.managers.connection_manager import subscription_manager


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
async def bulk_update_subscriptions(command: BulkUpdateSubscriptionsCommand):
    try:
        result = command_bus.handle(command)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    asyncio.create_task(subscription_manager.broadcast(command.user_id, {"subscriptions": result}))
    return result

@router.get("/analytics")
def get_subscription_analytics(user_id: int = Query(..., description="User ID for subscription analytics")):
    query = GetSubscriptionAnalyticsQuery(user_id=user_id)
    return query_bus.handle(query)

@router.get("/analytics/time_series")
def time_series_analytics(user_id: int = Query(...),
    group_by: str = Query("day"),
    start_date: Optional[str] = Query(None, description="Start date in ISO format"),
    end_date: Optional[str] = Query(None, description="End date in ISO format")):
    
    
    try:
        parsed_start_date = datetime.fromisoformat(start_date) if start_date else None
        parsed_end_date = datetime.fromisoformat(end_date) if end_date else None

        query = TimeSeriesSubscriptionAnalyticsQuery(
            user_id=user_id,
            group_by=group_by,
            start_date=parsed_start_date,
            end_date=parsed_end_date
        )
        
        return query_bus.handle(query)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/time_series/extended")
def time_series_analytics_extended(
    user_id: int = Query(...),
    group_by: str = Query("day"),
    start_date: Optional[str] = Query(None, description="Start date in ISO format"),
    end_date: Optional[str] = Query(None, description="End date in ISO format")
):
    # Parse incoming date strings into datetime objects, if provided.
    parsed_start_date = datetime.fromisoformat(start_date) if start_date else None
    parsed_end_date = datetime.fromisoformat(end_date) if end_date else None

    query = TimeSeriesSubscriptionAnalyticsQuery(
        user_id=user_id,
        group_by=group_by,
        start_date=parsed_start_date,
        end_date=parsed_end_date
    )
    
    return query_bus.handle(query)

@router.get("/analytics/segment")
def segmented_analytics(region: str):
    query = SegmentSubscriptionAnalyticsQuery(region=region)
    return query_bus.handle(query)

@router.get("/analytics/conversion")
def subscription_conversion_analytics(user_id: int):
    query = SubscriptionConversionMetricsQuery(user_id=user_id)
    return query_bus.handle(query)

@router.get("/analytics/predict")
def predictive_analytics(user_id: int, alert_type: str, forecast_days: int = 7):
    query = PredictiveSubscriptionAnalyticsQuery(user_id=user_id, alert_type=alert_type, forecast_days=forecast_days)
    return query_bus.handle(query)

@router.get("/analytics/predict/arima")
def predictive_analytics_arima(user_id: int = Query(...), alert_type: str = Query(...), forecast_days: int = Query(7)):
    query = EnhancedPredictiveSubscriptionAnalyticsQuery(user_id=user_id, alert_type=alert_type, forecast_days=forecast_days)
    return query_bus.handle(query)

@router.get("/analytics/predict/nn")
def predictive_analytics_nn(user_id: int = Query(...), alert_type: str = Query(...), forecast_days: int = Query(7)):
    query = EnhancedNeuralNetworkPredictiveAnalyticsQuery(user_id=user_id, alert_type=alert_type, forecast_days=forecast_days)
    return query_bus.handle(query)

@router.websocket("/ws")
async def subscriptions_ws(websocket: WebSocket, user_id: int = Query(...)):
    await subscription_manager.connect(user_id, websocket)
    try:
        # Optionally, you can send an initial state.
        with SessionLocal() as db:
            subscriptions = db.query(NotificationSubscription).filter(
                NotificationSubscription.user_id == user_id
            ).all()
            data = [
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
        await websocket.send_json(data)
        # Keep connection open.
        while True:
            # This connection now waits indefinitely. You can implement a ping/keepalive if needed.
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        subscription_manager.disconnect(user_id, websocket)
        print("User disconnected from subscriptions WS")

@router.get("/analytics/correlate_feedback", tags=["Analytics"])
def correlate_feedback_analytics(query: CorrelationAnalyticsQuery = Depends()):
    return query_bus.handle(query)