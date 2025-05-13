import math
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.infrastructure.models import Election, Vote, Voter

class ElectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_election(self, election: Election):
        self.db.add(election)
        self.db.commit()
        self.db.refresh(election)
        return election

    def get_election_by_id(self, election_id: int):
        return self.db.query(Election).filter(Election.id == election_id).first()
    
    def get_all_elections(self):
        return self.db.query(Election).all()
    
    def get_completed_elections(self):
        return self.db.query(Election).filter(Election.status == "completed").all()
    
    def get_candidate_support(self, election_id: int):
        # Fetch the election by ID
        election = self.db.query(Election).filter(Election.id == election_id).first()

        if not election:
            raise ValueError(f"Election with ID {election_id} not found.")

        # Parse candidates and votes
        candidates = election.candidates.split(",")
        votes = list(map(int, election.votes.split(",")))

        # Pair candidates with their respective vote counts
        return [{"candidate_name": candidates[i], "votes": votes[i]} for i in range(len(candidates))]

    def get_election_results(self, election_id: int):
        """Retrieve election results."""
        election = self.db.query(Election).filter(Election.id == election_id).first()
        if not election:
            return None

        candidates = election.candidates.split(",")
        votes = list(map(int, election.votes.split(",")))
        total_votes = sum(votes)

        results = [
            {
                "candidate": candidate,
                "votes": vote,
                "percentage": math.floor(vote / total_votes * 100) if total_votes > 0 else 0
            }
            for candidate, vote in zip(candidates, votes)
        ]

        return {"election_id": election.id, "results": results}
    
    def predict_turnout(self, election_id: int):
    # Retrieve past election voter turnout from actual votes
        turnout_data = self.db.query(Election.id, func.count(Vote.voter_id).label("voter_count")) \
                            .join(Vote, Vote.election_id == Election.id) \
                            .group_by(Election.id) \
                            .order_by(Election.id).all()

        # Ensure we only predict turnout when past data exists
        if not turnout_data or election_id not in [data.id for data in turnout_data]:
            return {"election_id": election_id, "predicted_turnout": 0, "status": "No Data"}

        # Apply moving average model based on past election turnout
        voter_counts = [data.voter_count for data in turnout_data]
        predicted_turnout = sum(voter_counts[-3:]) // len(voter_counts[-3:])

        return {
            "election_id": election_id,
            "predicted_turnout": predicted_turnout,
            "status": "Projected turnout based on actual votes cast"
        }
