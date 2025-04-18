@app.get("/elections/{election_id}/results/")
def get_election_results(election_id: int):
    query = GetElectionResultsQuery(election_id=election_id)
    election = election_repo.get_election_by_id(query.election_id)
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
    return {"results": election.votes}
