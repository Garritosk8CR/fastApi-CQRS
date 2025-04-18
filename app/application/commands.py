from pydantic import BaseModel
from typing import List

class RegisterVoterCommand(BaseModel):
    voter_id: int
    name: str


class CastVoteCommand(BaseModel):
    voter_id: int
    candidate: str

class CreateElectionCommand(BaseModel):
    name: str
    candidates: List[str]