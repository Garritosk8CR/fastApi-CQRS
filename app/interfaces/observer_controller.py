from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.application.commands import CreateObserverCommand
from app.application.query_bus import query_bus
from app.infrastructure.database import get_db
from fastapi import Form
from app.application.handlers import command_bus

router = APIRouter(prefix="/observer", tags=["Observer"])
templates = Jinja2Templates(directory="app/templates")

@router.post("/")
def create_observer(query: CreateObserverCommand, db: Session = Depends(get_db)):
    try:
        return command_bus.handle(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))