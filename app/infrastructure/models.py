from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table, Enum
from sqlalchemy.orm import relationship
from app.infrastructure.database import Base
import enum

class Voter(Base):
    __tablename__ = "voters"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    has_voted = Column(Boolean, default=False)

class ElectionStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"

class Election(Base):
    __tablename__ = "elections"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    candidates = Column(String)
    votes = Column(String)
    status = Column(Enum(ElectionStatus), default=ElectionStatus.ACTIVE)  # Comma-separated votes count (e.g., "0,2,5")

    def increment_vote(self, candidate_name: str):
        candidate_list = self.candidates.split(",")
        vote_counts = list(map(int, self.votes.split(",")))
        try:
            index = candidate_list.index(candidate_name)
            vote_counts[index] += 1
            self.votes = ",".join(map(str, vote_counts))
        except ValueError:
            raise ValueError("Candidate not found")
