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