from pydantic import BaseModel

class RegisterVoterCommand(BaseModel):
    voter_id: int
    name: str


class CastVoteCommand(BaseModel):
    voter_id: int
    candidate: str
