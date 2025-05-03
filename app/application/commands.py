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