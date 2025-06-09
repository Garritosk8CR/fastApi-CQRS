from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class GetElectionResultsQuery:
    def __init__(self, election_id: int):
        self.election_id = election_id

class GetVoterDetailsQuery:
    def __init__(self, voter_id: int):
        self.voter_id = voter_id

class CheckVoterExistsQuery:
    def __init__(self, voter_id: int):
        self.voter_id = voter_id

class GetAllElectionsQuery:
    pass  # No parameters are required for fetching all elections

class GetElectionDetailsQuery:
    def __init__(self, election_id: int):
        self.election_id = election_id

class GetVotingPageDataQuery:
    pass  # No parameters needed since we fetch all voters and elections

class GetUserByEmailQuery:
    def __init__(self, email: str):
        self.email = email

class GetUserProfileQuery(BaseModel):
    user_id: int

class ListUsersQuery(BaseModel):
    page: int
    page_size: int

class HasVotedQuery(BaseModel):
    user_id: int

class GetUserByIdQuery(BaseModel):
    user_id: int

class ListAdminsQuery(BaseModel):
    page: int = 1
    page_size: int = 10

from pydantic import BaseModel

class UsersByRoleQuery(BaseModel):
    role: str
    page: int = 1
    page_size: int = 10

class VotingStatusQuery(BaseModel):
    pass

class CandidateSupportQuery(BaseModel):
    election_id: int

class ElectionTurnoutQuery(BaseModel):
    election_id: int

class VoterDetailsQuery(BaseModel):
    voter_id: int

class UserStatisticsQuery(BaseModel):
    pass

class ElectionSummaryQuery(BaseModel):
    pass

class TopCandidateQuery(BaseModel):
    election_id: int

class ParticipationByRoleQuery(BaseModel):
    election_id: int

class InactiveVotersQuery(BaseModel):
    pass

class ResultsBreakdownQuery(BaseModel):
    election_id: int

class GetPollingStationQuery(BaseModel):
    station_id: int

class GetPollingStationsByElectionQuery(BaseModel):
    election_id: int

class GetAuditLogsQuery(BaseModel):
    election_id: int

class ExportElectionResultsQuery(BaseModel):
    election_id: int
    format: str = "json"

class GetObserversQuery(BaseModel):
    election_id: int

class GetObserverByIdQuery(BaseModel):
    observer_id: int

class GetCandidatesQuery(BaseModel):
    election_id: int

class GetCandidateByIdQuery(BaseModel):
    candidate_id: int

class GetVotesByElectionQuery(BaseModel):
    election_id: int

class GetVotesByVoterQuery(BaseModel):
    voter_id: int

class GetFeedbackByElectionQuery(BaseModel):
    election_id: int

class GetFeedbackBySeverityQuery(BaseModel):
    severity: str

class GetIntegrityScoreQuery(BaseModel):
    election_id: int

class GetSeverityDistributionQuery(BaseModel):
    pass  # No input required for this query

class GetTopObserversQuery(BaseModel):
    limit: int = 10  # Default: Top 10 observers

class GetTimePatternsQuery(BaseModel):
    pass  # No input required

class GetSentimentAnalysisQuery(BaseModel):
    pass  # No input required

class GetTurnoutPredictionQuery(BaseModel):
    election_id: int

class GetObserverTrustScoresQuery(BaseModel):
    pass  # No input needed

class GetFeedbackExportQuery(BaseModel):
    export_format: str = "json"

class GetElectionSummaryQuery(BaseModel):
    election_id: int

class GetSentimentTrendQuery(BaseModel):
    election_id: int

class GetFeedbackCategoryAnalyticsQuery(BaseModel):
    election_id: int

class GetCandidateVoteDistributionQuery(BaseModel):
    election_id: int

class GetTimeBasedVotingPatternsQuery(BaseModel):
    election_id: int
    interval: str = "hourly"  # Supports "hourly" or "daily"

class GetHistoricalTurnoutTrendsQuery(BaseModel):
    election_ids: list[int]

class GetTurnoutPredictionQuery(BaseModel):
    election_id: int
    lookback: int = 3  # Default to using last 3 elections

class GetSeasonalTurnoutPredictionQuery(BaseModel):
    election_id: int
    lookback: int = 5  # Default to using last 5 elections
    weight_factor: float = 1.5  # Higher weight applied to matching seasons

class GetTurnoutConfidenceQuery(BaseModel):
    election_id: int
    lookback: int = 5  # Use last 5 elections by default

class GetDetailedHistoricalComparisonsQuery(BaseModel):
    election_ids: List[int]

class GetDetailedHistoricalComparisonsWithExternalQuery(BaseModel):
    election_ids: List[int]

class DashboardAnalyticsQuery(BaseModel):
    election_id: int

class RealTimeElectionSummaryQuery(BaseModel):
    election_id: int

class GeolocationAnalyticsQuery(BaseModel):
    election_id: int

class PollingStationAnalyticsQuery(BaseModel):
    election_id: int

class HistoricalPollingStationTrendsQuery(BaseModel):
    election_ids: List[int]
    polling_station_id: Optional[int] = None

class PredictiveVoterTurnoutQuery(BaseModel):
    upcoming_election_id: int

class AnomalyDetectionQuery(BaseModel):
    election_id: int

class GeolocationTrendsQuery(BaseModel):
    election_id: int
    region: Optional[str] = None  # Optional filter to restrict to a specific region.

class GetAlertsQuery(BaseModel):
    election_id: Optional[int] = None

class GetAlertsWSQuery(BaseModel):
    election_id: Optional[int] = None
    status: Optional[str] = None  # e.g., "new", "acknowledged", "resolved"

class GetNotificationsQuery(BaseModel):
    user_id: int

# New query for the summary.
class GetNotificationsSummaryQuery(BaseModel):
    user_id: int

class GetSubscriptionsQuery(BaseModel):
    user_id: int

class GetSubscriptionAnalyticsQuery(BaseModel):
    user_id: int

class TimeSeriesSubscriptionAnalyticsQuery(BaseModel):
    user_id: int
    group_by: str = "day"  # Options: "day", "week", "month"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class SegmentSubscriptionAnalyticsQuery(BaseModel):
    region: str

class SubscriptionConversionMetricsQuery(BaseModel):
    user_id: int

class PredictiveSubscriptionAnalyticsQuery(BaseModel):
    user_id: int
    alert_type: str
    forecast_days: int = 7

class EnhancedPredictiveSubscriptionAnalyticsQuery(BaseModel):
    user_id: int
    alert_type: str
    forecast_days: int = 7

class EnhancedNeuralNetworkPredictiveAnalyticsQuery(BaseModel):
    user_id: int
    alert_type: str
    forecast_days: int = 7