from application.commands import CreateElectionCommand
from infrastructure.models import Election

@app.get("/elections/{election_id}/results/")
def get_election_results(election_id: int):
    query = GetElectionResultsQuery(election_id=election_id)
    election = election_repo.get_election_by_id(query.election_id)
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
    return {"results": election.votes}

@app.post("/elections/")
def create_election(command: CreateElectionCommand, db: Session = Depends(get_db)):
    repo = ElectionRepository(db)
    
    # Create a new election
    new_election = Election(
        name=command.name,
        candidates=",".join(command.candidates),
        votes=",".join(["0"] * len(command.candidates))  # Initialize votes to zero
    )
    
    created_election = repo.create_election(new_election)
    return {"message": "Election created successfully", "election_id": created_election.id}

