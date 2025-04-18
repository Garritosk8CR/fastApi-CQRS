class RegisterVoterCommand:
    def __init__(self, voter_id: int, name: str):
        self.voter_id = voter_id
        self.name = name

class CastVoteCommand:
    def __init__(self, voter_id: int, candidate: str):
        self.voter_id = voter_id
        self.candidate = candidate
