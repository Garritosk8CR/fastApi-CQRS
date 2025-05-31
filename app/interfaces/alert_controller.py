import asyncio
import csv
from io import StringIO
from typing import List
from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.application.commands import CastVoteCommand, CastVoteCommandv2, CreateAlertCommand
from app.application.queries import GetAlertsQuery
from app.application.query_bus import query_bus
from app.infrastructure.database import get_db
from app.application.handlers import command_bus
from app.infrastructure.models import AlertResponse

router = APIRouter(prefix="/alerts", tags=["Alerts"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_model=List[AlertResponse])
def list_alerts(
    election_id: int = Query(None, description="Filter alerts by election ID")
):
    query_model = GetAlertsQuery(election_id=election_id)
    return query_bus.handle(query_model)

@router.post("/", response_model=AlertResponse)
def create_alert(
    election_id: int,
    alert_type: str,
    message: str
):
    command = CreateAlertCommand(election_id=election_id, alert_type=alert_type, message=message)
    return command_bus.handle(command)