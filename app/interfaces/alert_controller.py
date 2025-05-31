import asyncio
import csv
from io import StringIO
from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.application.commands import CastVoteCommand, CastVoteCommandv2
from app.application.queries import AnomalyDetectionQuery, DashboardAnalyticsQuery, GeolocationAnalyticsQuery, GeolocationTrendsQuery, GetCandidateVoteDistributionQuery, GetDetailedHistoricalComparisonsQuery, GetDetailedHistoricalComparisonsWithExternalQuery, GetElectionSummaryQuery, GetHistoricalTurnoutTrendsQuery, GetSeasonalTurnoutPredictionQuery, GetSentimentTrendQuery, GetTimeBasedVotingPatternsQuery, GetTurnoutConfidenceQuery, GetTurnoutPredictionQuery, GetVotesByElectionQuery, GetVotesByVoterQuery, HistoricalPollingStationTrendsQuery, PollingStationAnalyticsQuery, PredictiveVoterTurnoutQuery, RealTimeElectionSummaryQuery
from app.application.query_bus import query_bus
from app.infrastructure.database import get_db
from app.application.handlers import command_bus

router = APIRouter(prefix="/alerts", tags=["Alerts"])
templates = Jinja2Templates(directory="app/templates")