from app.domain.election import Election
from app.infrastructure.database import election_database

class ElectionRepository:
    def create_election(self, election: Election):
        election_database[election.election_id] = election

    def get_election_by_id(self, election_id: int) -> Election:
        return election_database.get(election_id)
