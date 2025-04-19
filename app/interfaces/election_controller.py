from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.application.query_bus import query_bus
from app.application.queries import GetAllElectionsQuery
from app.infrastructure.database import get_db
from app.application.commands import CreateElectionCommand
from app.infrastructure.models import Election
from app.infrastructure.election_repo import ElectionRepository
from app.application.commands import CreateElectionCommand
from app.application.handlers import command_bus

router = APIRouter()  # Define the router object

@router.post("/elections/")
def create_election(command: CreateElectionCommand):
    try:
        election = command_bus.handle(command)  # Dispatch the command to the handler
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "message": "Election created successfully",
        "election_id": election.id
    }

@router.get("/elections/{election_id}/")
def get_election_details(election_id: int, db: Session = Depends(get_db)):
    repo = ElectionRepository(db)
    election = repo.get_election_by_id(election_id)
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")

    return {
        "election_id": election.id,
        "name": election.name,
        "candidates": election.candidates.split(","),
        "votes": list(map(int, election.votes.split(",")))
    }

@router.get("/elections/")
def list_all_elections():
    query = GetAllElectionsQuery()
    elections = query_bus.handle(query)  # Delegate the query to the bus
    return elections

@router.put("/elections/{election_id}/end/")
def end_election(election_id: int, db: Session = Depends(get_db)):
    repo = ElectionRepository(db)
    election = repo.get_election_by_id(election_id)
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
    
    election.status = "completed"
    db.commit()
    return {"message": f"Election {election_id} has been ended successfully."}

@router.get("/elections/{election_id}/results/")
def get_election_results(election_id: int, db: Session = Depends(get_db)):
    repo = ElectionRepository(db)
    election = repo.get_election_by_id(election_id)
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
    
    return {
        "results": {candidate: vote for candidate, vote in zip(election.candidates.split(","), election.votes.split(","))}
    }
