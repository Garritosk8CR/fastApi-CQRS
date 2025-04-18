from fastapi import FastAPI, HTTPException
from app.application.commands import RegisterVoterCommand, CastVoteCommand
from app.infrastructure.voter_repo import VoterRepository
from app.infrastructure.election_repo import ElectionRepository
from app.domain.voter import Voter

app = FastAPI()
voter_repo = VoterRepository()
election_repo = ElectionRepository()

@app.post("/voters/")
def register_voter(command: RegisterVoterCommand):
    new_voter = Voter(voter_id=command.voter_id, name=command.name)
    voter_repo.register_voter(new_voter)
    return {"message": "Voter registered successfully"}

@app.post("/voters/{voter_id}/vote/")
def cast_vote(voter_id: int, command: CastVoteCommand):
    voter = voter_repo.get_voter_by_id(voter_id)
    if not voter:
        raise HTTPException(status_code=404, detail="Voter not found")
    if voter.has_voted:
        raise HTTPException(status_code=400, detail="Voter has already voted")
    election = election_repo.get_election_by_id(1)  # Assume election_id is 1
    try:
        election.add_vote(command.candidate)
        voter.has_voted = True
        return {"message": f"Vote cast successfully for {command.candidate}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
