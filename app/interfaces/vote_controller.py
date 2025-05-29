import asyncio
import csv
from io import StringIO
from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.application.commands import CastVoteCommand, CastVoteCommandv2
from app.application.queries import AnomalyDetectionQuery, DashboardAnalyticsQuery, GeolocationAnalyticsQuery, GetCandidateVoteDistributionQuery, GetDetailedHistoricalComparisonsQuery, GetDetailedHistoricalComparisonsWithExternalQuery, GetElectionSummaryQuery, GetHistoricalTurnoutTrendsQuery, GetSeasonalTurnoutPredictionQuery, GetSentimentTrendQuery, GetTimeBasedVotingPatternsQuery, GetTurnoutConfidenceQuery, GetTurnoutPredictionQuery, GetVotesByElectionQuery, GetVotesByVoterQuery, HistoricalPollingStationTrendsQuery, PollingStationAnalyticsQuery, PredictiveVoterTurnoutQuery, RealTimeElectionSummaryQuery
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

@router.get("/analytics/geolocation")
def get_geolocation_analytics(election_id: int):
    query = GeolocationAnalyticsQuery(election_id=election_id)
    return query_bus.handle(query)

@router.get("/analytics/polling_station")
def get_polling_station_analytics(election_id: int):
    """
    Returns basic performance metrics for polling stations for the specified election.
    """
    query = PollingStationAnalyticsQuery(election_id=election_id)
    return query_bus.handle(query)

@router.get("/analytics/historical_polling_station_trends")
def historical_polling_station_trends(
    election_ids: str = Query(..., description="Comma separated list of election IDs"),
    polling_station_id: int = Query(None, description="Optional polling station ID to filter by")
):
    # Convert comma-separated string to a list of ints
    ids = list(map(int, election_ids.split(",")))
    query = HistoricalPollingStationTrendsQuery(election_ids=ids, polling_station_id=polling_station_id)
    return query_bus.handle(query)

@router.get("/analytics/predictive_voter_turnout")
def predictive_voter_turnout(
    upcoming_election_id: int = Query(..., description="The ID for the upcoming election for turnout prediction")
):
    query = PredictiveVoterTurnoutQuery(upcoming_election_id=upcoming_election_id)
    return query_bus.handle(query)

@router.get("/analytics/anomalies")
def detect_anomalies(election_id: int):
    """
    Detect anomalies in polling station performance for a given election.
    """
    query = AnomalyDetectionQuery(election_id=election_id)
    return query_bus.handle(query)

@router.get("/analytics/export_results")
def export_election_results(
    election_id: int = Query(..., description="The election ID to export results for"),
    export_format: str = Query("json", description="Export format: 'json' or 'csv'")
):
    """
    Exports the polling station analytics for the given election. Supports JSON and CSV output.
    """
    query = PollingStationAnalyticsQuery(election_id=election_id)
    data = query_bus.handle(query)
    
    if export_format.lower() == "csv":
        # Create CSV output using StringIO and the csv module.
        output = StringIO()
        writer = csv.writer(output)

        # Write header row.
        header = [
            "polling_station_id",
            "polling_station_name",
            "total_votes",
            "average_interval_seconds",
            "peak_hour",
            "votes_in_peak_hour"
        ]
        writer.writerow(header)
        
        # Write data rows.
        for entry in data:
            polling_station = entry.get("polling_station", {})
            row = [
                polling_station.get("id"),
                polling_station.get("name"),
                entry.get("total_votes"),
                entry.get("average_interval_seconds"),
                entry.get("peak_hour"),
                entry.get("votes_in_peak_hour")
            ]
            writer.writerow(row)
        
        output.seek(0)
        response = StreamingResponse(output, media_type="text/csv")
        response.headers["Content-Disposition"] = f"attachment; filename=election_{election_id}_results.csv"
        return response
    else:
        # Default to JSON export.
        return JSONResponse(content=data)

@router.websocket("/ws/election/{election_id}")
async def realtime_election_summary_ws(websocket: WebSocket, election_id: int):
    """
    Establish a WebSocket connection that continuously sends real-time election summary updates.
    """
    await websocket.accept()
    try:
        while True:
            # Use our existing handler to get the real-time summary.
            query = RealTimeElectionSummaryQuery(election_id=election_id)
            summary = query_bus.handle(query)
            
            # Send the updated summary to the client.
            await websocket.send_json(summary)
            
            # Wait a few seconds before sending the next update.
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        # Handle disconnection gracefully.
        print("Client disconnected from real-time updates")

