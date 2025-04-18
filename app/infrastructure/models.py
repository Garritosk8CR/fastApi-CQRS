from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.infrastructure.database import Base

class Voter(Base):
    __tablename__ = "voters"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    has_voted = Column(Boolean, default=False)

class Election(Base):
    __tablename__ = "elections"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    candidates = Column(String)  # Comma-separated list of candidates
    votes = Column(String)  # Comma-separated votes count (e.g., "0,2,5")

    def increment_vote(self, candidate_name: str):
        candidate_list = self.candidates.split(",")
        vote_counts = list(map(int, self.votes.split(",")))
        try:
            index = candidate_list.index(candidate_name)
            vote_counts[index] += 1
            self.votes = ",".join(map(str, vote_counts))
        except ValueError:
            raise ValueError("Candidate not found")
