from typing import List
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table, Enum
from sqlalchemy.orm import relationship
from app.infrastructure.database import Base
import enum

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


class ElectionResponse(BaseModel):
    election_id: int
    name: str
    candidates: List[str]
    votes: List[int]

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)
    password = Column(String)
    role = Column(String, default="voter")
    
    # Relationship with Voter
    voter = relationship("Voter", uselist=False, back_populates="user")

class Voter(Base):
    __tablename__ = "voters"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    has_voted = Column(Boolean, default=False)

    # Relationship with User
    user = relationship("User", back_populates="voter")

class UserSignUp(BaseModel):
    name: str
    email: EmailStr
    password: str


