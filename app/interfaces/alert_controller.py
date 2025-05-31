import asyncio
import csv
from io import StringIO
from typing import List
from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.application.commands import CreateAlertCommand, UpdateAlertCommand
from app.application.queries import GetAlertsQuery, GetAlertsWSQuery
from app.application.query_bus import query_bus
from app.infrastructure.database import SessionLocal, get_db
from app.application.handlers import command_bus
from app.infrastructure.models import Alert, AlertResponse

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

@router.put("/{alert_id}", response_model=AlertResponse)
def update_alert(
    alert_id: int,
    command: UpdateAlertCommand
):
    print(f"Command: {command}")
    # Override command.alert_id with the path parameter.
    # command.alert_id = alert_id
    try:
        return command_bus.handle(command)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.websocket("/ws")
async def alerts_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Build the CQRS query with status filter "new"
            query = GetAlertsWSQuery(status="new")
            data = query_bus.handle(query)
            await websocket.send_json(data)
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        print("Client disconnected")