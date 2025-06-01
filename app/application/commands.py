from pydantic import BaseModel, EmailStr
from typing import List, Optional

class RegisterVoterCommand(BaseModel):
    voter_id: int
    name: str
    email: str
    password: str


class CastVoteCommand(BaseModel):
    voter_id: int
    election_id: int
    candidate: str


class CreateElectionCommand(BaseModel):
    name: str
    candidates: List[str]

class CheckVoterExistsQuery:
    def __init__(self, voter_id: int):
        self.voter_id = voter_id

class EndElectionCommand(BaseModel):
    election_id: int

class UserSignUp(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginUserCommand(BaseModel):
    email: EmailStr
    password: str

class EditUserCommand(BaseModel):
    name: str
    email: EmailStr
    password: str

class UpdateUserRoleCommand(BaseModel):
    user_id: int
    role: str

class CreatePollingStationCommand(BaseModel):
    name: str
    location: str
    election_id: int
    capacity: int

class UpdatePollingStationCommand(BaseModel):
    station_id: int
    name: str = None
    location: str = None
    capacity: int = None

class DeletePollingStationCommand(BaseModel):
    station_id: int

class CreateAuditLogCommand(BaseModel):
    election_id: int
    performed_by: int
    action: str
    details: Optional[str] = None

class CreateObserverCommand(BaseModel):
    name: str
    email: str
    election_id: int
    organization: Optional[str] = None

class UpdateObserverCommand(BaseModel):
    observer_id: int
    name: Optional[str] = None
    email: Optional[str] = None
    organization: Optional[str] = None

class DeleteObserverCommand(BaseModel):
    observer_id: int

class CreateCandidateCommand(BaseModel):
    name: str
    party: Optional[str] = None
    bio: Optional[str] = None
    election_id: int

class UpdateCandidateCommand(BaseModel):
    candidate_id: int
    name: Optional[str] = None
    party: Optional[str] = None
    bio: Optional[str] = None

class DeleteCandidateCommand(BaseModel):
    candidate_id: int

class CastVoteCommandv2(BaseModel):
    voter_id: int
    candidate_id: int
    election_id: int

class SubmitFeedbackCommand(BaseModel):
    observer_id: int
    election_id: int
    description: str
    severity: str  # "LOW", "MEDIUM", "HIGH"

class CreateAlertCommand(BaseModel):
    election_id: int
    alert_type: str
    message: str

class UpdateAlertCommand(BaseModel):
    alert_id: int
    status: str   # e.g., "acknowledged", "resolved"

class MarkNotificationReadCommand(BaseModel):
    notification_id: int