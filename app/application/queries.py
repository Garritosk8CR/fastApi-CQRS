from typing import List
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