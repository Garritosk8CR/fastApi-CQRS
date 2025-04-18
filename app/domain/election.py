class Election:
    def __init__(self, election_id: int, candidates: list[str]):
        self.election_id = election_id
        self.candidates = candidates
        self.votes = {candidate: 0 for candidate in candidates}

    def add_vote(self, candidate: str):
        if candidate in self.votes:
            self.votes[candidate] += 1
        else:
            raise ValueError("Candidate not found")
