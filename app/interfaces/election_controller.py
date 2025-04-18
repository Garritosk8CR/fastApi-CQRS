from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.application.commands import CreateElectionCommand
from app.infrastructure.models import Election
from app.infrastructure.election_repo import ElectionRepository

router = APIRouter()  # Define the router object

@router.post("/elections/")
def create_election(command: CreateElectionCommand, db: Session = Depends(get_db)):
    repo = ElectionRepository(db)
    
    new_election = Election(
        name=command.name,
        candidates=",".join(command.candidates),
        votes=",".join(["0"] * len(command.candidates))
    )
    created_election = repo.create_election(new_election)
    return {"message": "Election created successfully", "election_id": created_election.id}

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
def list_all_elections(db: Session = Depends(get_db)):
    repo = ElectionRepository(db)
    elections = db.query(Election).all()
    
    return [
        {
            "election_id": election.id,
            "name": election.name,
            "candidates": election.candidates.split(","),
            "votes": list(map(int, election.votes.split(",")))
        }
        for election in elections
    ]

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
