from fastapi import APIRouter, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.application.commands import CreateCandidateCommand, DeleteCandidateCommand, UpdateCandidateCommand
from app.application.queries import GetCandidatesQuery
from app.application.query_bus import query_bus
from app.infrastructure.database import get_db
from app.application.handlers import command_bus


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

@router.patch("/{candidate_id}")
def update_candidate(candidate_id: int, query: UpdateCandidateCommand, db: Session = Depends(get_db)):
    try:
        return command_bus.handle(query)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.delete("/{candidate_id}")
def delete_candidate(candidate_id: int, db: Session = Depends(get_db)):
    query = DeleteCandidateCommand(candidate_id=candidate_id)
    try:
        return command_bus.handle(query)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))