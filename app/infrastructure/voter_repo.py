from app.domain.voter import Voter
from app.infrastructure.database import voter_database

class VoterRepository:
    def register_voter(self, voter: Voter):
        voter_database[voter.voter_id] = voter

    def get_voter_by_id(self, voter_id: int) -> Voter:
        return voter_database.get(voter_id)
