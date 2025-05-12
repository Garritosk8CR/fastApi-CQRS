import pytest
from fastapi.testclient import TestClient
from app.infrastructure.models import Candidate, Election, Observer, ObserverFeedback, User, Voter
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

# Initialize TestClient for the FastAPI app
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
def create_test_observers(test_db):
    def _create_observers(observers_data):
        observers = []
        for observer_data in observers_data:
            observer = Observer(**observer_data)
            test_db.add(observer)
            observers.append(observer)
        test_db.commit()
        return observers
    return _create_observers

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
def create_test_feedback(test_db):
    def _create_feedback(feedback_data):
        feedbacks = []
        for feedback in feedback_data:
            observer_feedback = ObserverFeedback(**feedback)
            test_db.add(observer_feedback)
            feedbacks.append(observer_feedback)
        test_db.commit()
        return feedbacks
    return _create_feedback

def test_submit_feedback_success(test_db, create_test_elections, create_test_observers, client):
    # Arrange: Create an election and an observer
    elections_data = [{"id": 1, "name": "General Election"}]
    create_test_elections(elections_data)
    observers_data = [
        {"id": 1, "name": "Observer A", "email": "observerA@example.com", "election_id": 1, "organization": "Group X"},
        {"id": 2, "name": "Observer B", "email": "observerB@example.com", "election_id": 1, "organization": "Group Y"},
    ]
    create_test_observers(observers_data)
    
    

    request_data = {
        "observer_id": 1,
        "election_id": 1,
        "description": "Polling station irregularities noticed.",
        "severity": "HIGH"
    }

    # Act: Call the endpoint
    response = client.post("/observer_feedback", json=request_data)

    # Assert: Verify feedback submission
    assert response.status_code == 200
    assert response.json()["description"] == "Polling station irregularities noticed."
    assert response.json()["severity"] == "HIGH"

    test_db.rollback()
    gc.collect()

def test_get_feedback_by_election(test_db, create_test_feedback, create_test_elections, create_test_observers, client):
    elections_data = [{"id": 1, "name": "General Election"}]
    create_test_elections(elections_data)
    observers_data = [
        {"id": 1, "name": "Observer A", "email": "observerA@example.com", "election_id": 1, "organization": "Group X"},
        {"id": 2, "name": "Observer B", "email": "observerB@example.com", "election_id": 1, "organization": "Group Y"},
    ]
    create_test_observers(observers_data)
    # Arrange: Create feedback entries
    feedback_data = [
        {"id": 1, "observer_id": 1, "election_id": 1, "description": "Unverified voters spotted.", "severity": "MEDIUM", "timestamp": "2025-05-10T00:57:00"},
        {"id": 2, "observer_id": 2, "election_id": 1, "description": "Ballot tampering suspected.", "severity": "HIGH", "timestamp": "2025-05-10T01:00:00"},
    ]
    create_test_feedback(feedback_data)

    # Act: Call the endpoint
    response = client.get("/observer_feedback/elections/1/observer_feedback")

    # Assert: Verify correct filtering
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["severity"] == "MEDIUM"

    test_db.rollback()
    gc.collect()

def test_get_feedback_by_severity(test_db, create_test_feedback, create_test_elections, create_test_observers, client):
    elections_data = [{"id": 1, "name": "General Election"}]
    create_test_elections(elections_data)
    observers_data = [
        {"id": 1, "name": "Observer A", "email": "observerA@example.com", "election_id": 1, "organization": "Group X"},
        {"id": 2, "name": "Observer B", "email": "observerB@example.com", "election_id": 1, "organization": "Group Y"},
    ]
    create_test_observers(observers_data)
    # Arrange: Create feedback entries
    feedback_data = [
        {"id": 1, "observer_id": 1, "election_id": 1, "description": "Unauthorized access reported.", "severity": "HIGH", "timestamp": "2025-05-10T00:57:00"},
    ]
    create_test_feedback(feedback_data)

    # Act: Call the endpoint
    response = client.get("/observer_feedback/severity/HIGH")

    # Assert: Verify correct retrieval
    assert response.status_code == 200
    assert response.json()[0]["description"] == "Unauthorized access reported."

    test_db.rollback()
    gc.collect()

def test_missing_fields_handling(test_db, create_test_elections, create_test_observers, client):
    elections_data = [{"id": 1, "name": "General Election"}]
    create_test_elections(elections_data)
    observers_data = [
        {"id": 1, "name": "Observer A", "email": "observerA@example.com", "election_id": 1, "organization": "Group X"},
        {"id": 2, "name": "Observer B", "email": "observerB@example.com", "election_id": 1, "organization": "Group Y"},
    ]
    create_test_observers(observers_data)
    # Arrange: Missing severity in payload
    request_data = {
        "observer_id": 1,
        "election_id": 1,
        "description": "Security concerns raised."
    }

    # Act: Call the endpoint
    response = client.post("/observer_feedback", json=request_data)

    # Assert: Verify rejection
    assert response.status_code == 422  # Validation error
    assert "severity" in response.json()["detail"][0]["loc"]

    test_db.rollback()
    gc.collect()

def test_invalid_observer_submission(test_db, create_test_elections, client):

    elections_data = [{"id": 1, "name": "General Election"}]
    create_test_elections(elections_data)
    # Act: Try submitting feedback from a non-existent observer
    request_data = {
        "observer_id": 999,  # Observer doesn't exist
        "election_id": 1,
        "description": "Voting fraud suspected.",
        "severity": "HIGH"
    }

    response = client.post("/observer_feedback", json=request_data)

    # Assert: Verify rejection
    assert response.status_code == 400
    assert response.json()["detail"] == "Observer with ID 999 not found."

    test_db.rollback()
    gc.collect()

def test_integrity_score_election_with_reports(test_db, create_test_elections, create_test_feedback, create_test_observers, client):
    # Arrange: Create an election and feedback entries
    elections_data = [{"id": 1, "name": "National Election"}]
    feedback_data = [
        {"id": 1, "observer_id": 1, "election_id": 1, "description": "Ballot tampering suspected.", "severity": "HIGH"},
        {"id": 2, "observer_id": 2, "election_id": 1, "description": "Unverified voters spotted.", "severity": "MEDIUM"},
        {"id": 3, "observer_id": 3, "election_id": 1, "description": "Minor issue with polling station staff.", "severity": "LOW"},
    ]

    observers_data = [
        {"id": 1, "name": "Observer A", "email": "observerA@example.com", "election_id": 1, "organization": "Group X"},
        {"id": 2, "name": "Observer B", "email": "observerB@example.com", "election_id": 1, "organization": "Group Y"},
        {"id": 3, "name": "Observer C", "email": "observerC@example.com", "election_id": 1, "organization": "Group Z"},
    ]
    

    create_test_elections(elections_data)
    create_test_observers(observers_data)
    create_test_feedback(feedback_data)

    # Act: Call the endpoint
    response = client.get("/observer_feedback/elections/1/integrity_score")

    # Assert: Verify risk score calculation
    assert response.status_code == 200
    assert response.json()["election_id"] == 1
    assert response.json()["status"] in ["Moderate", "Critical"]  # Ensuring valid risk assessment

    test_db.rollback()
    gc.collect()

def test_integrity_score_election_with_no_reports(test_db, create_test_elections, client):
    # Arrange: Create an election without feedback
    elections_data = [{"id": 1, "name": "Local Election"}]
    create_test_elections(elections_data)

    # Act: Call the endpoint
    response = client.get("/observer_feedback/elections/1/integrity_score")

    # Assert: Verify default stability score
    assert response.status_code == 200
    assert response.json()["election_id"] == 1
    assert response.json()["risk_score"] == 0
    assert response.json()["status"] == "Stable"

    test_db.rollback()
    gc.collect()

def test_integrity_score_election_with_low_reports(test_db, create_test_elections, create_test_feedback, create_test_observers, client):
    # Arrange: Create an election with only LOW severity feedback
    elections_data = [{"id": 1, "name": "State Election"}]
    feedback_data = [
        {"id": 1, "observer_id": 1, "election_id": 1, "description": "Minor miscommunication at polling station.", "severity": "LOW"},
        {"id": 2, "observer_id": 2, "election_id": 1, "description": "Delayed opening at one polling station.", "severity": "LOW"},
    ]
    observers_data = [
        {"id": 1, "name": "Observer A", "email": "observerA@example.com", "election_id": 1, "organization": "Group X"},
        {"id": 2, "name": "Observer B", "email": "observerB@example.com", "election_id": 1, "organization": "Group Y"},
    ]
    
    create_test_elections(elections_data)
    create_test_observers(observers_data)
    create_test_feedback(feedback_data)

    # Act: Call the endpoint
    response = client.get("/observer_feedback/elections/1/integrity_score")

    # Assert: Verify minimal risk impact
    assert response.status_code == 200
    assert response.json()["election_id"] == 1
    assert response.json()["status"] == "Stable"

    test_db.rollback()
    gc.collect()

def test_integrity_score_election_with_high_risk_reports(test_db, create_test_elections, create_test_feedback, create_test_observers, client):
    # Arrange: Create an election with multiple HIGH severity reports
    elections_data = [{"id": 1, "name": "Presidential Election"}]
    feedback_data = [
        {"id": 1, "observer_id": 1, "election_id": 1, "description": "Votes missing from final count.", "severity": "HIGH"},
        {"id": 2, "observer_id": 2, "election_id": 1, "description": "Attempted voter suppression detected.", "severity": "HIGH"},
        {"id": 3, "observer_id": 3, "election_id": 1, "description": "Polling station security breached.", "severity": "HIGH"},
    ]
    observers_data = [
        {"id": 1, "name": "Observer A", "email": "observerA@example.com", "election_id": 1, "organization": "Group X"},
        {"id": 2, "name": "Observer B", "email": "observerB@example.com", "election_id": 1, "organization": "Group Y"},
        {"id": 3, "name": "Observer C", "email": "observerC@example.com", "election_id": 1, "organization": "Group Z"},
    ]
    

    create_test_elections(elections_data)
    create_test_observers(observers_data)
    create_test_feedback(feedback_data)

    # Act: Call the endpoint
    response = client.get("/observer_feedback/elections/1/integrity_score")

    # Assert: Verify critical risk designation
    assert response.status_code == 200
    assert response.json()["election_id"] == 1
    assert response.json()["status"] == "Critical"

    test_db.rollback()
    gc.collect()