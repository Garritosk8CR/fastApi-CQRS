from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.application.commands import CreateCandidateCommand
from app.application.queries import GetCandidatesQuery
from app.application.query_bus import query_bus
from app.infrastructure.database import get_db
from fastapi import Form
from app.application.handlers import command_bus
from app.infrastructure.models import Observer

router = APIRouter(prefix="/candidates", tags=["Candidate"])
templates = Jinja2Templates(directory="app/templates")

@router.post("/")
def create_candidate(query: CreateCandidateCommand, db: Session = Depends(get_db)):
    try:
        return command_bus.handle(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/elections/{election_id}/candidates")
def get_candidates(election_id: int, db: Session = Depends(get_db)):
    query = GetCandidatesQuery(election_id=election_id)
    return query_bus.handle(query)