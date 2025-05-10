from fastapi import APIRouter, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.application.commands import CastVoteCommand
from app.application.queries import GetVotesByElectionQuery
from app.application.query_bus import query_bus
from app.infrastructure.database import get_db
from app.application.handlers import command_bus

router = APIRouter(prefix="/votes", tags=["Votes"])
templates = Jinja2Templates(directory="app/templates")

@router.post("/")
def cast_vote(query: CastVoteCommand, db: Session = Depends(get_db)):
    try:
        return command_bus.handle(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/elections/{election_id}/votes")
def get_votes_by_election(election_id: int, db: Session = Depends(get_db)):
    query = GetVotesByElectionQuery(election_id=election_id)
    return query_bus.handle(query)