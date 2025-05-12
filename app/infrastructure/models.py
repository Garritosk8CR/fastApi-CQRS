from datetime import datetime, timezone
from typing import List
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, DateTime, Integer, String, Boolean, ForeignKey, Table, Enum
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

    polling_stations = relationship("PollingStation", back_populates="election")
    audit_logs = relationship("AuditLog", back_populates="election")
    observers = relationship("Observer", back_populates="election")
    candidatesv2 = relationship("Candidate", back_populates="election")
    vote = relationship("Vote", back_populates="election")
    observer_feedback = relationship("ObserverFeedback", back_populates="election")

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
    audit_logs = relationship("AuditLog", back_populates="user")

class Voter(Base):
    __tablename__ = "voters"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    has_voted = Column(Boolean, default=False)

    # Relationship with User
    user = relationship("User", back_populates="voter")
    votes = relationship("Vote", back_populates="voter")

class PollingStation(Base):
    __tablename__ = "polling_stations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    election_id = Column(Integer, ForeignKey("elections.id"), nullable=False)
    capacity = Column(Integer, nullable=False)

    election = relationship("Election", back_populates="polling_stations")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    election_id = Column(Integer, ForeignKey("elections.id"), nullable=False)
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)
    details = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)

    election = relationship("Election", back_populates="audit_logs")
    user = relationship("User")

class Observer(Base):
    __tablename__ = "observers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    election_id = Column(Integer, ForeignKey("elections.id"), nullable=False)
    organization = Column(String, nullable=True)

    election = relationship("Election", back_populates="observers")
    feedback = relationship("ObserverFeedback", back_populates="observer")

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    party = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    election_id = Column(Integer, ForeignKey("elections.id"), nullable=False)

    election = relationship("Election", back_populates="candidatesv2")

class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    voter_id = Column(Integer, ForeignKey("voters.id"), nullable=False)  # Linked to Voter
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    election_id = Column(Integer, ForeignKey("elections.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)

    voter = relationship("Voter", back_populates="votes")
    candidate = relationship("Candidate")
    election = relationship("Election", back_populates="vote")

class ObserverFeedback(Base):
    __tablename__ = "observer_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    observer_id = Column(Integer, ForeignKey("observers.id"), nullable=False)
    election_id = Column(Integer, ForeignKey("elections.id"), nullable=False)
    description = Column(String, nullable=False)
    severity = Column(String, nullable=False)  # e.g., "LOW", "MEDIUM", "HIGH"
    timestamp = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)

    observer = relationship("Observer", back_populates="feedback")
    election = relationship("Election", back_populates="observer_feedback")
    
class VoterData(BaseModel):
    name: str
    email: str
    role: str

class VoterUploadQuery(BaseModel):
    voters: List[VoterData]



