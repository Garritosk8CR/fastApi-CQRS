from fastapi import APIRouter, HTTPException
from app.application.query_bus import query_bus
from app.application.queries import GetAllElectionsQuery, GetElectionDetailsQuery, GetElectionResultsQuery
from app.application.commands import CreateElectionCommand, EndElectionCommand
from app.infrastructure.models import ElectionResponse
from app.application.commands import CreateElectionCommand
from app.application.handlers import command_bus

router = APIRouter()  # Define the router object



@router.post("/elections/new", response_model=ElectionResponse)
def create_election(command: CreateElectionCommand):
    try:
        # Dispatch the command and get the election object
        election = command_bus.handle(command)
        if election is None:
            print("Election creation failed")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return election  
@router.get("/elections/")
def list_all_elections():
    query = GetAllElectionsQuery()
    elections = query_bus.handle(query)  # Delegate the query to the bus
    return elections

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


@router.put("/elections/{election_id}/end/")
def end_election(election_id: int):
    command = EndElectionCommand(election_id=election_id)
    
    try:
        result = command_bus.handle(command)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.get("/elections/{election_id}/results/")
def get_election_results(election_id: int):
    query = GetElectionResultsQuery(election_id)

    try:
        result = query_bus.handle(query)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

