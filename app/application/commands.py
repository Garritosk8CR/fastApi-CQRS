from pydantic import BaseModel, EmailStr
from typing import List
from pydantic import BaseModel

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

