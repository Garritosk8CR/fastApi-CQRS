from fastapi import APIRouter, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.application.query_bus import query_bus
from app.infrastructure.database import get_db
from app.application.handlers import command_bus

router = APIRouter(prefix="/votes", tags=["Votes"])
templates = Jinja2Templates(directory="app/templates")