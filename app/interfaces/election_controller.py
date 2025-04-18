from fastapi import Depends, HTTPException
from app.application.queries import GetElectionResultsQuery
from app.infrastructure import election_repo
from app.infrastructure.database import SessionLocal
from app.infrastructure.election_repo import ElectionRepository
from application.commands import CreateElectionCommand
from infrastructure.models import Election

@app.get("/elections/{election_id}/results/")
def get_election_results(election_id: int):
    query = GetElectionResultsQuery(election_id=election_id)
    election = election_repo.get_election_by_id(query.election_id)
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
    return {"results": election.votes}

@app.get("/elections/{election_id}/")
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

@app.put("/elections/{election_id}/end/")
def end_election(election_id: int, db: Session = Depends(get_db)):
    repo = ElectionRepository(db)
    election = repo.get_election_by_id(election_id)
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
    
    # Update the status to completed
    election.status = "completed"
    db.commit()
    return {"message": f"Election {election_id} has been ended successfully."}

@app.get("/elections/")
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

