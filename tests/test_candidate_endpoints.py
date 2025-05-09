import datetime
import pytest
from fastapi.testclient import TestClient
from app.infrastructure.models import AuditLog, Candidate, Election, Observer, PollingStation, User, Voter
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

def test_create_candidate(test_db, create_test_elections, client): 
    # Arrange: Create an election before adding candidates
    elections_data = [{"id": 1, "name": "Presidential Election"}]
    create_test_elections(elections_data)

    request_data = {
        "name": "Candidate One",
        "party": "Progressive Party",
        "bio": "A leader dedicated to social change.",
        "election_id": 1
    }

    # Act: Call the endpoint
    response = client.post("/candidates", json=request_data)

    # Assert: Verify creation
    assert response.status_code == 200
    assert response.json()["name"] == "Candidate One"
    assert response.json()["party"] == "Progressive Party"

    test_db.rollback()
    gc.collect()

def test_get_candidates_by_election(test_db, create_test_candidates, create_test_elections, client):
    elections_data = [{"id": 1, "name": "Presidential Election"}]
    create_test_elections(elections_data)
    # Arrange: Create candidates linked to an election
    candidates_data = [
        {"id": 1, "name": "Candidate A", "party": "Group X", "bio": "Experienced leader.", "election_id": 1},
        {"id": 2, "name": "Candidate B", "party": "Group Y", "bio": "Visionary thinker.", "election_id": 1},
    ]
    create_test_candidates(candidates_data)

    # Act: Call the endpoint
    response = client.get("/candidates/elections/1/candidates")

    # Assert: Verify correct filtering
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["name"] == "Candidate A"

    test_db.rollback()
    gc.collect()

def test_get_candidate_by_id(test_db, create_test_candidates, create_test_elections, client):
    elections_data = [{"id": 1, "name": "Presidential Election"}]
    create_test_elections(elections_data)
    # Arrange: Create a candidate
    candidates_data = [
        {"id": 1, "name": "Candidate C", "party": "Independent", "bio": "Advocate for reform.", "election_id": 1}
    ]
    create_test_candidates(candidates_data)

    # Act: Call the endpoint
    response = client.get("/candidates/1")

    # Assert: Verify correct retrieval
    assert response.status_code == 200
    assert response.json()["name"] == "Candidate C"
    assert response.json()["party"] == "Independent"

    test_db.rollback()
    gc.collect()

def test_update_candidate(test_db, create_test_candidates, create_test_elections, client):
    elections_data = [{"id": 1, "name": "Presidential Election"}]
    create_test_elections(elections_data)
    # Arrange: Create a candidate
    candidates_data = [
        {"id": 1, "name": "Candidate D", "party": "Old Party", "bio": "Traditional values.", "election_id": 1}
    ]
    create_test_candidates(candidates_data)

    update_data = {
        "candidate_id": 1,
        "name": "Updated Candidate",
        "party": "Modern Party",
        "bio": "Progressive approach to governance."
    }

    # Act: Call the endpoint
    response = client.patch("/candidates/1", json=update_data)

    # Assert: Verify update
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Candidate"
    assert response.json()["party"] == "Modern Party"

    test_db.rollback()
    gc.collect()