from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.application.commands import SubmitFeedbackCommand
from app.application.queries import GetFeedbackByElectionQuery, GetFeedbackBySeverityQuery, GetFeedbackCategoryAnalyticsQuery, GetFeedbackExportQuery, GetIntegrityScoreQuery, GetObserverByIdQuery, GetObserverTrustScoresQuery, GetSentimentAnalysisQuery, GetSeverityDistributionQuery, GetTimePatternsQuery, GetTopObserversQuery
from app.application.query_bus import query_bus
from app.infrastructure.database import get_db
from app.application.handlers import command_bus

router = APIRouter(prefix="/observer_feedback", tags=["Feedback"])
templates = Jinja2Templates(directory="app/templates")

@router.post("/")
def submit_feedback(query: SubmitFeedbackCommand):
    try:
        query_Observer = GetObserverByIdQuery(observer_id=query.observer_id)
        observer = query_bus.handle(query_Observer)
        if not observer:
            raise ValueError("Observer ID not found.")
        return command_bus.handle(query)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/elections/{election_id}/observer_feedback")
def get_feedback_by_election(election_id: int):
    query = GetFeedbackByElectionQuery(election_id=election_id)
    return query_bus.handle(query)

@router.get("/severity/{severity}")
def get_feedback_by_severity(severity: str):
    query = GetFeedbackBySeverityQuery(severity=severity)
    return query_bus.handle(query)

@router.get("/elections/{election_id}/integrity_score")
def get_integrity_score(election_id: int):
    query = GetIntegrityScoreQuery(election_id=election_id)
    
    return query_bus.handle(query)

@router.get("/severity_distribution")
def get_severity_distribution():
    query = GetSeverityDistributionQuery()
    return query_bus.handle(query)

@router.get("/top_observers")
def get_top_observers(limit: int = 10):
    query = GetTopObserversQuery(limit=limit) 
    return query_bus.handle(query)

@router.get("/time_patterns")
def get_time_patterns():
    query = GetTimePatternsQuery()
    return query_bus.handle(query)

@router.get("/sentiment_analysis")
def get_sentiment_analysis():
    query = GetSentimentAnalysisQuery()
    return query_bus.handle(query)

@router.get("/reliability_scores")
def get_observer_trust_scores():
    query = GetObserverTrustScoresQuery()
    return query_bus.handle(query)

@router.get("/export")
def export_observer_feedback(export_format: str = "json"):
    query = GetFeedbackExportQuery(export_format=export_format)
    result = query_bus.handle(query)
    
    if export_format.lower() == "csv":
        return Response(content=result, media_type="text/csv")
    return result

@router.get("/analytics/feedback_category")
def get_feedback_category_analytics(election_id: int):
    query = GetFeedbackCategoryAnalyticsQuery(election_id=election_id)
    return query_bus.handle(query)