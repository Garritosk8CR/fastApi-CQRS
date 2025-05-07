from fastapi import APIRouter, HTTPException
from app.application.query_bus import query_bus
from app.application.commands import RegisterVoterCommand, CastVoteCommand
from app.application.handlers import HasVotedHandler, command_bus
from app.application.queries import HasVotedQuery, InactiveVotersQuery, VoterDetailsQuery, VotingStatusQuery
from app.infrastructure.models import VoterUploadQuery


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

@router.get("/users/{user_id}/has-voted")
def get_has_voted(
    user_id: int
):
    # Create and process the query
    query = HasVotedQuery(user_id=user_id)

    try:
        result = query_bus.handle(query)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/users/voting-status")
def voting_status():
    # Create and process the query
    query = VotingStatusQuery()
    result = query_bus.handle(query)
    return result

@router.get("/voter/{voter_id}")
def voter_details(voter_id: int):
    query = VoterDetailsQuery(voter_id=voter_id)

    try:
        result = query_bus.handle(query)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    
@router.get("/inactive/")
def inactive_voters():
    query = InactiveVotersQuery()
    try:
        result = query_bus.handle(query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    
@router.post("/bulk-upload")
def bulk_voter_upload(query: VoterUploadQuery):
    try:
        return command_bus.handle(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

