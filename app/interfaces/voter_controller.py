from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.application.commands import RegisterVoterCommand, CastVoteCommand
from app.infrastructure.models import Voter
from app.infrastructure.database import get_db
from app.infrastructure.voter_repo import VoterRepository
from app.infrastructure.election_repo import ElectionRepository
from app.application.handlers import command_bus


router = APIRouter()

@router.post("/voters/")
def register_voter(command: RegisterVoterCommand):
    try:
        command_bus.handle(command)  # Dispatch the command to the handler
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred!")

    return {"message": "Voter registered successfully"}

@router.post("/voters/{voter_id}/vote/")
def cast_vote(voter_id: int, command: CastVoteCommand, db: Session = Depends(get_db)):
    voter_repo = VoterRepository(db)
    election_repo = ElectionRepository(db)

    # Validate voter existence
    voter = voter_repo.get_voter_by_id(voter_id)
    if not voter:
        raise HTTPException(status_code=404, detail="Voter not found")
    if voter.has_voted:
        raise HTTPException(status_code=400, detail="Voter has already voted")

    # Retrieve election by ID
    election = election_repo.get_election_by_id(1)  # Assuming election_id is always 1 for simplicity
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")

    try:
        # Increment vote count for the selected candidate
        election.increment_vote(command.candidate)
        voter.has_voted = True  # Mark voter as having voted
        db.commit()  # Persist changes to the database

        return {"message": f"Vote cast successfully for {command.candidate}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

