from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from application.commands import RegisterVoterCommand, CastVoteCommand
from infrastructure.models import Voter
from infrastructure.database import get_db
from infrastructure.voter_repo import VoterRepository
from infrastructure.election_repo import ElectionRepository

router = APIRouter()

@router.post("/voters/")
def register_voter(command: RegisterVoterCommand, db: Session = Depends(get_db)):
    repo = VoterRepository(db)
    voter = Voter(name=command.name, has_voted=False)
    registered_voter = repo.register_voter(voter)
    return {"id": registered_voter.id, "message": "Voter registered successfully"}

@router.post("/voters/{voter_id}/vote/")
def cast_vote(voter_id: int, command: CastVoteCommand, db: Session = Depends(get_db)):
    voter_repo = VoterRepository(db)
    election_repo = ElectionRepository(db)

    voter = voter_repo.get_voter_by_id(voter_id)
    if not voter:
        raise HTTPException(status_code=404, detail="Voter not found")
    if voter.has_voted:
        raise HTTPException(status_code=400, detail="Voter has already voted")

    election = election_repo.get_election_by_id(1)  # Assuming election_id is 1
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")

    try:
        election.increment_vote(command.candidate)
        voter.has_voted = True
        db.commit()
        return {"message": f"Vote cast successfully for {command.candidate}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
