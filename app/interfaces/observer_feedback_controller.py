from fastapi import APIRouter, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.application.commands import SubmitFeedbackCommand
from app.application.query_bus import query_bus
from app.infrastructure.database import get_db
from app.application.handlers import command_bus

router = APIRouter(prefix="/observer_feedback", tags=["Feedback"])
templates = Jinja2Templates(directory="app/templates")

@router.post("/")
def submit_feedback(query: SubmitFeedbackCommand):
    try:
        return command_bus.handle(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))