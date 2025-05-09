from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.application.commands import CreateObserverCommand, DeleteObserverCommand, UpdateObserverCommand
from app.application.queries import GetObserverByIdQuery, GetObserversQuery
from app.application.query_bus import query_bus
from app.infrastructure.database import get_db
from fastapi import Form
from app.application.handlers import command_bus
from app.infrastructure.models import Observer

router = APIRouter(prefix="/observers", tags=["Observer"])
templates = Jinja2Templates(directory="app/templates")

@router.post("/")
def create_observer(query: CreateObserverCommand, db: Session = Depends(get_db)):
    try:
        return command_bus.handle(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/{observer_id}")
def get_observer_by_id(observer_id: int, db: Session = Depends(get_db)):
    query = GetObserverByIdQuery(observer_id=observer_id)
    try:
        return query_bus.handle(query)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.get("/elections/{election_id}/observers")
def get_observers(election_id: int, db: Session = Depends(get_db)):
    query = GetObserversQuery(election_id=election_id)
    return query_bus.handle(query)

@router.patch("/{observer_id}", response_model=None)
def update_observer(observer_id: int, query: UpdateObserverCommand, db: Session = Depends(get_db)):
    try:
        return command_bus.handle(query)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.delete("/{observer_id}")
def delete_observer(observer_id: int, db: Session = Depends(get_db)):
    query = DeleteObserverCommand(observer_id=observer_id)
    try:
        return command_bus.handle(query)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))