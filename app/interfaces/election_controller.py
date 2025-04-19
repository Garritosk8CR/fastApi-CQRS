from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.application.query_bus import query_bus
from app.application.queries import GetAllElectionsQuery, GetElectionDetailsQuery
from app.infrastructure.database import get_db
from app.application.commands import CreateElectionCommand
from app.infrastructure.models import Election, ElectionResponse
from app.infrastructure.election_repo import ElectionRepository
from app.application.commands import CreateElectionCommand
from app.application.handlers import command_bus

router = APIRouter()  # Define the router object

@router.post("/elections/", response_model=ElectionResponse)
def create_election(command: CreateElectionCommand):
    try:
        # Dispatch the command and get the election object
        election = command_bus.handle(command)
        if election is None:
            print("Election creation failed")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    print(election)
    # Return the election object as JSON
    return election  # Return the created election as a JSON response

@router.get("/elections/{election_id}/")
def get_election_details(election_id: int):
    query = GetElectionDetailsQuery(election_id)
    try:
        election = query_bus.handle(query)  # Dispatch the query
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

    return election

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
