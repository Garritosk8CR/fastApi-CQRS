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

router = APIRouter(prefix="/candidates", tags=["Candidate"])
templates = Jinja2Templates(directory="app/templates")