from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.application.commands import CreatePollingStationCommand, DeletePollingStationCommand, UpdatePollingStationCommand
from app.application.queries import GetPollingStationQuery, GetPollingStationsByElectionQuery
from app.application.query_bus import query_bus
from app.infrastructure.database import get_db
from app.security import get_current_complete_user, get_current_user
from fastapi import Form
from app.application.handlers import command_bus

router = APIRouter(prefix="/polling-stations", tags=["Polling Stations"])
templates = Jinja2Templates(directory="app/templates")

@router.post("/")
def create_polling_station(query: CreatePollingStationCommand):
    try:
        return command_bus.handle(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/{station_id}")
def get_polling_station(station_id: int):
    query = GetPollingStationQuery(station_id=station_id)
    try:
        return query_bus.get_polling_station(query)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.get("/elections/{election_id}/polling-stations")
def get_polling_stations_by_election(election_id: int):
    query = GetPollingStationsByElectionQuery(election_id=election_id)
    return query_bus.get_polling_stations_by_election(query)

@router.patch("/{station_id}")
def update_polling_station(station_id: int, query: UpdatePollingStationCommand):
    try:
        return command_bus.update_polling_station(query)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.delete("/{station_id}")
def delete_polling_station(station_id: int):
    query = DeletePollingStationCommand(station_id=station_id)
    try:
        return command_bus.delete_polling_station(query)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))