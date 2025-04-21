from fastapi import APIRouter, HTTPException
from app.application.commands import RegisterVoterCommand, CastVoteCommand
from app.application.handlers import command_bus


router = APIRouter()

@router.post("/voters/")
def register_voter(command: RegisterVoterCommand):
    try:
        print(f"Command: {command}")
        new_voter = command_bus.handle(command)  # Dispatch the command to the handler
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

    return {"message": "Voter registered successfully", "voter": new_voter}

@router.post("/voters/{voter_id}/elections/{election_id}/cast_vote/")
def cast_vote(voter_id: int, election_id: int, command: CastVoteCommand):
    try:
        # Dispatch the command
        result = command_bus.handle(command)
        return {"message": f"Vote cast successfully for {result['candidate']}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


