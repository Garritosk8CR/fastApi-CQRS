import pytest
from fastapi.testclient import TestClient
from app.infrastructure.models import AuditLog, Candidate, Election, Observer, PollingStation, User, Vote, Voter
from app.main import app  # Import the FastAPI instance from main.py
from app.infrastructure.database import Base, SessionLocal, engine
import gc

@pytest.fixture(scope="module")
def test_db():
    # Ensure the database schema is created
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    yield db
    # Tear down the database after tests
    db.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    # Create tables for the test database
    Base.metadata.create_all(bind=engine)
    yield
    # Drop all tables after the test
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as client:
        yield client

@pytest.fixture
def create_test_elections(test_db):
    def _create_elections(elections_data):
        elections = []
        for election_data in elections_data:
            election = Election(**election_data)
            test_db.add(election)
            elections.append(election)
        test_db.commit()
        return elections
    return _create_elections

@pytest.fixture
def create_test_candidates(test_db):
    def _create_candidates(candidates_data):
        candidates = []
        for candidate_data in candidates_data:
            candidate = Candidate(**candidate_data)
            test_db.add(candidate)
            candidates.append(candidate)
        test_db.commit()
        return candidates
    return _create_candidates

@pytest.fixture
def create_test_voters(test_db):
    def _create_voters(voters_data):
        voters = []
        for voter_data in voters_data:
            voter = Voter(**voter_data)
            test_db.add(voter)
            voters.append(voter)
        test_db.commit()
        return voters
    return _create_voters

@pytest.fixture
def create_test_votes(test_db):
    def _create_votes(votes_data):
        votes = []
        for vote_data in votes_data:
            vote = Vote(**vote_data)
            test_db.add(vote)
            votes.append(vote)
        test_db.commit()
        return votes
    return _create_votes

@pytest.fixture
def create_test_users(test_db):
    def _create_users(users_data):
        users = []
        for user_data in users_data:
            user = User(**user_data)
            test_db.add(user)
            users.append(user)
        test_db.commit()
        return users
    return _create_users

def test_cast_vote_success(test_db, create_test_elections, create_test_candidates, create_test_voters,create_test_users, client):
    # Arrange: Create an election, candidate, and voter
    users_data = [{"id": 1, "name": "Admin User", "email": "admin@example.com"}]
    elections_data = [{"id": 1, "name": "Presidential Election"}]
    candidates_data = [{"id": 1, "name": "Candidate A", "party": "Independent", "bio": "Leader for change.", "election_id": 1}]
    voters_data = [{"id": 1, "user_id": 1, "has_voted": False}]

    create_test_users(users_data)
    create_test_elections(elections_data)
    create_test_candidates(candidates_data)
    create_test_voters(voters_data)

    request_data = {
        "voter_id": 1,
        "candidate_id": 1,
        "election_id": 1
    }

    # Act: Call the endpoint
    response = client.post("/votes", json=request_data)

    # Assert: Verify vote logging
    print(response.json())
    assert response.status_code == 200
    assert response.json()["voter_id"] == 1
    assert response.json()["candidate_id"] == 1

    test_db.rollback()
    gc.collect()

def test_get_votes_by_election(test_db, create_test_votes, create_test_elections, create_test_candidates, create_test_users, create_test_voters, client):
    # Arrange: Create votes linked to an election
    users_data = [{"id": 1, "name": "Admin User", "email": "admin@example.com"}, {"id": 2, "name": "Voter User 1", "email": "voter1@example.com"}]
    elections_data = [{"id": 1, "name": "Presidential Election"}]
    candidates_data = [{"id": 1, "name": "Candidate A", "party": "Independent", "bio": "Leader for change.", "election_id": 1}, {"id": 2, "name": "Candidate B", "party": "Democratic", "bio": "Protects the American people.", "election_id": 1}]
    votes_data = [
        {"id": 1, "voter_id": 1, "candidate_id": 1, "election_id": 1, "timestamp": "2025-05-10T00:57:00"},
        {"id": 2, "voter_id": 2, "candidate_id": 2, "election_id": 1, "timestamp": "2025-05-10T01:00:00"},
    ]
    voters_data = [{"id": 1, "user_id": 1, "has_voted": False}, {"id": 2, "user_id": 2, "has_voted": True}]

    create_test_users(users_data)
    create_test_elections(elections_data)
    create_test_candidates(candidates_data)
    create_test_voters(voters_data)
    create_test_votes(votes_data)
    

    # Act: Call the endpoint
    response = client.get("/votes/elections/1/votes")

    # Assert: Verify correct filtering
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["candidate_id"] == 1

    test_db.rollback()
    gc.collect()