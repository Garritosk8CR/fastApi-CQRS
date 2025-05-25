from fastapi import APIRouter, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.application.commands import CastVoteCommand, CastVoteCommandv2
from app.application.queries import DashboardAnalyticsQuery, GetCandidateVoteDistributionQuery, GetDetailedHistoricalComparisonsQuery, GetDetailedHistoricalComparisonsWithExternalQuery, GetElectionSummaryQuery, GetHistoricalTurnoutTrendsQuery, GetSeasonalTurnoutPredictionQuery, GetSentimentTrendQuery, GetTimeBasedVotingPatternsQuery, GetTurnoutConfidenceQuery, GetTurnoutPredictionQuery, GetVotesByElectionQuery, GetVotesByVoterQuery, RealTimeElectionSummaryQuery
from app.application.query_bus import query_bus
from app.infrastructure.database import get_db
from app.application.handlers import command_bus

router = APIRouter(prefix="/votes", tags=["Votes"])
templates = Jinja2Templates(directory="app/templates")

@router.post("/")
def cast_vote(query: CastVoteCommandv2, db: Session = Depends(get_db)):
    try:
        return command_bus.handle(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/elections/{election_id}/votes")
def get_votes_by_election(election_id: int, db: Session = Depends(get_db)):
    query = GetVotesByElectionQuery(election_id=election_id)
    return query_bus.handle(query)

@router.get("/voters/{voter_id}/votes")
def get_votes_by_voter(voter_id: int, db: Session = Depends(get_db)):
    query = GetVotesByVoterQuery(voter_id=voter_id)
    return query_bus.handle(query)

@router.get("/analytics/election_summary")
def get_election_summary(election_id: int):
    query = GetElectionSummaryQuery(election_id=election_id)
    return query_bus.handle(query)

@router.get("/analytics/sentiment_trend")
def get_sentiment_trend(election_id: int):
    query = GetSentimentTrendQuery(election_id=election_id)
    return query_bus.handle(query)

@router.get("/analytics/candidate_distribution")
def candidate_distribution(election_id: int):
    query = GetCandidateVoteDistributionQuery(election_id=election_id)
    return query_bus.handle(query)

@router.get("/analytics/voting_patterns")
def get_time_based_voting_patterns(election_id: int, interval: str = "hourly"):
    query = GetTimeBasedVotingPatternsQuery(election_id=election_id, interval=interval)
    return query_bus.handle(query)

@router.get("/analytics/turnout_trends")
def get_historical_turnout_trends(election_ids: str):
    # Convert election IDs from query string to list of integers
    try:
        print(election_ids)
        election_ids_list = list(map(int, election_ids.split(",")))
        query = GetHistoricalTurnoutTrendsQuery(election_ids=election_ids_list)
        return query_bus.handle(query)
    except ValueError:
        print(f"Invalid election IDs: {election_ids}")
        raise HTTPException(status_code=400, detail="Invalid election IDs")

@router.get("/analytics/turnout_forecast")
def get_turnout_forecast(election_id: int, lookback: int = 3, db: Session = Depends(get_db)):
    query = GetTurnoutPredictionQuery(election_id=election_id, lookback=lookback)
    return query_bus.handle(query)

@router.get("/analytics/turnout_forecast/seasonal")
def get_seasonal_turnout_forecast(election_id: int, lookback: int = 5, weight_factor: float = 1.5):
    query = GetSeasonalTurnoutPredictionQuery(election_id=election_id, lookback=lookback, weight_factor=weight_factor)
    return query_bus.handle(query)

@router.get("/analytics/turnout_forecast/confidence")
def get_turnout_confidence(election_id: int, lookback: int = 5):
    query = GetTurnoutConfidenceQuery(election_id=election_id, lookback=lookback)
    return query_bus.handle(query)

@router.get("/analytics/historical_detailed")
def get_detailed_historical_comparisons(election_ids: str):
    # Convert comma-separated string to a list of integers
    election_ids_list = list(map(int, election_ids.split(",")))
    query = GetDetailedHistoricalComparisonsQuery(election_ids=election_ids_list)
    return query_bus.handle(query)
    
@router.get("/analytics/historical_detailed/external")
def get_detailed_historical_comparisons_with_external(election_ids: str):
    # Convert a comma-separated string of election IDs to a list of integers.
    election_ids_list = list(map(int, election_ids.split(",")))
    query = GetDetailedHistoricalComparisonsWithExternalQuery(election_ids=election_ids_list)
    return query_bus.handle(query)

@router.get("/analytics/dashboard")
def get_dashboard(election_id: int):
    query = DashboardAnalyticsQuery(election_id=election_id)
    return query_bus.handle(query)

@router.get("/analytics/real_time_summary")
def real_time_election_summary(election_id: int):
    query = RealTimeElectionSummaryQuery(election_id=election_id)
    return query_bus.handle(query)