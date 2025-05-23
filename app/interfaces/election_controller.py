from fastapi import APIRouter, HTTPException
from app.application.query_bus import query_bus
from app.application.queries import CandidateSupportQuery, ElectionSummaryQuery, ElectionTurnoutQuery, ExportElectionResultsQuery, GetAllElectionsQuery, GetElectionDetailsQuery, GetElectionResultsQuery, GetTurnoutPredictionQuery, ParticipationByRoleQuery, ResultsBreakdownQuery, TopCandidateQuery
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
    
@router.get("/{election_id}/candidate-support")
def candidate_support(
    election_id: int
):
    query = CandidateSupportQuery(election_id=election_id)

    try:
        result = query_bus.handle(query)
        return {"candidates": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    
@router.get("/{election_id}/turnout")
def election_turnout(
    election_id: int
):
    query = ElectionTurnoutQuery(election_id=election_id)

    try:
        result = query_bus.handle(query)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

@router.get("/summary/")
def election_summary():
    query = ElectionSummaryQuery()

    try:
        result = query_bus.handle(query)
        return {"elections": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    
@router.get("/{election_id}/top-candidate/")
def top_candidate(election_id: int):
    query = TopCandidateQuery(election_id=election_id)
    try:
        result = query_bus.handle(query)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    
@router.get("/{election_id}/participation-by-role/")
def participation_by_role(
    election_id: int
):
    query = ParticipationByRoleQuery(election_id=election_id)

    try:
        result = query_bus.handle(query)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred.{str(e)}")
    
@router.get("/{election_id}/results-breakdown/")
def results_breakdown(election_id: int):
    query = ResultsBreakdownQuery(election_id=election_id)
    
    try:
        result = query_bus.handle(query)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    
@router.get("/{election_id}/export-results/")
def export_results(election_id: int, format: str = "json"):
    query = ExportElectionResultsQuery(election_id=election_id, format=format)
    try:
        return query_bus.handle(query)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.get("/{election_id}/turnout_prediction")
def get_turnout_prediction(election_id: int):  
    query = GetTurnoutPredictionQuery(election_id=election_id)
    return query_bus.handle(query)