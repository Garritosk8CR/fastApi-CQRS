import csv
from datetime import datetime, timedelta, timezone
import io
import pytest
from fastapi.testclient import TestClient
from app.infrastructure.models import Candidate, Election, Observer, ObserverFeedback, PollingStation, User, Vote, Voter, Alert
from app.main import app  # Import the FastAPI instance from main.py
from app.infrastructure.database import Base, SessionLocal, engine
import gc

# Use a fresh test database

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
def create_test_voter(test_db):
    def _create_voter(user_data, voter_data):
        # Create a user
        if user_data:
            user = User(**user_data)
            test_db.add(user)
            test_db.flush()  # Flush to generate the user ID
            voter_data["user_id"] = user.id
        else:
            user = None

        # Create a voter
        voter = Voter(**voter_data)
        test_db.add(voter)
        test_db.commit()
        return user, voter
    return _create_voter

@pytest.fixture
def create_test_user_and_voter(test_db):
    def _create_user_and_voter(user_id, name, email, has_voted):
        # Create a user
        user = User(id=user_id, name=name, email=email, role="voter")
        test_db.add(user)
        test_db.flush()  # Ensure the user is added before creating a voter

        # Create a voter
        voter = Voter(user_id=user_id, has_voted=has_voted)
        test_db.add(voter)
        test_db.commit()

        return user, voter
    return _create_user_and_voter

@pytest.fixture
def create_test_votes(test_db):
    def _create(vote_data):
        votes = []
        for data in vote_data:
            vote = Vote(**data)
            test_db.add(vote)
            votes.append(vote)
        test_db.commit()
        return votes
    return _create

@pytest.fixture
def create_test_voters(test_db):
    def _create_voters(users_data, voters_data):
        users = []
        voters = []

        # Create users
        for user_data in users_data:
            user = User(**user_data)
            test_db.add(user)
            users.append(user)

        test_db.flush()  # Ensure users are added before creating voters

        # Create voters
        for voter_data in voters_data:
            voter = Voter(**voter_data)
            test_db.add(voter)
            voters.append(voter)

        test_db.commit()
        return users, voters
    return _create_voters

@pytest.fixture
def get_voter_count(test_db):
    """Helper fixture to count voters in the database."""
    return lambda: test_db.query(User).count()

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
    def _create(feedback_data):
        feedbacks = []
        for data in feedback_data:
            feedback = ObserverFeedback(**data)
            test_db.add(feedback)
            feedbacks.append(feedback)
        test_db.commit()
        return feedbacks
    return _create

@pytest.fixture
def create_test_polling_stations(test_db):
    def _create_stations(stations_data):
        stations = []
        for station_data in stations_data:
            station = PollingStation(**station_data)
            test_db.add(station)
            stations.append(station)
        test_db.commit()
        return stations
    return _create_stations

@pytest.fixture
def create_test_alert(test_db):
    def create_alert(election_id: int, alert_type: str, message: str, status: str = "new"):
        alert = Alert(
            election_id=election_id,
            alert_type=alert_type,
            message=message,
            status=status,
            created_at=datetime.now(timezone.utc)
        )
        test_db.add(alert)
        test_db.commit()
        test_db.refresh(alert)
        return alert
    return create_alert

@pytest.fixture
def create_test_election(test_db):
    def create_election(id: int, name: str):
        election = Election(id=id, name=name)
        test_db.add(election)
        test_db.commit()
        test_db.refresh(election)
        return election
    return create_election

def test_alerts_ws_empty(client, test_db):
    """
    Test that when no new alerts exist, the WebSocket returns an empty list.
    """
    with client.websocket_connect("/alerts/ws") as websocket:
        # Receive the first message from the WebSocket
        data = websocket.receive_json()
        gc.collect()
        test_db.rollback()
        assert isinstance(data, list), "Expected a list of alerts"
        assert len(data) == 0, "Expected no alerts, but found some"

def test_alerts_ws_with_alert(client, test_db, create_test_elections):
    create_test_elections([{"id": 1, "name": "Election Region Trends"}])
    """
    Test that when a new alert is created, the WebSocket returns that alert.
    """
    # Create a new alert with status "new"
    alert = Alert(
        election_id=1,
        alert_type="anomaly",
        message="Test alert for websocket",
        status="new",
        created_at=datetime.now(timezone.utc)
    )
    
    # Insert the alert into the test database
    with SessionLocal() as db:
        db.add(alert)
        db.commit()
        db.refresh(alert)
    
    with client.websocket_connect("/alerts/ws") as websocket:
        # The WebSocket endpoint sends updates every 5 seconds.
        # The first message should be sent immediately.
        data = websocket.receive_json()

        gc.collect()
        test_db.rollback()

        assert isinstance(data, list), "Expected a list of alerts"
        
        # Look for the alert by its ID.
        found_alert = None
        for item in data:
            if item.get("id") == alert.id:
                found_alert = item
                break
        assert found_alert is not None, "Newly created alert not found in WebSocket response"
        assert found_alert.get("message") == "Test alert for websocket"
        assert found_alert.get("status") == "new"

# ---------------------------------------------------------------------------
# Test GET /alerts Endpoint
# ---------------------------------------------------------------------------
def test_get_alerts_empty(client, test_db):
    """
    When no alerts exist, GET /alerts should return an empty list.
    """
    response = client.get("/alerts")

    gc.collect()
    test_db.rollback()

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0

def test_get_alerts_filter_by_election(client, test_db, create_test_election, create_test_alert):
    """
    Create two elections and several alerts.
    Then verify that using the election filter returns only matching alerts.
    """
    
    election1 = create_test_election(id=1, name="Election One")
    election2 = create_test_election(id=2, name="Election Two")
    # Create alerts belonging to each election.
    alert1 = create_test_alert(election_id=election1.id, alert_type="anomaly", message="Alert for election one")
    alert2 = create_test_alert(election_id=election2.id, alert_type="fraud", message="Alert for election two")
    
    # When filtering by election_id=1, we should only return the first alert.
    response = client.get("/alerts?election_id=1")

    gc.collect()
    test_db.rollback()

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["election_id"] == 1
    assert data[0]["message"] == "Alert for election one"

# ---------------------------------------------------------------------------
# Test POST /alerts Endpoint
# ---------------------------------------------------------------------------
def test_create_alert(client, test_db, create_test_election):
    """
    POST /alerts should create a new alert and return it.
    """
    # Make sure there's an election for the alert.
    
    create_test_election(id=1, name="Election Three")
    
    params = {
        "election_id": 1,
        "alert_type": "anomaly",
        "message": "Test alert created via POST"
    }
    response = client.post("/alerts", params=params)

    gc.collect()
    test_db.rollback()

    assert response.status_code == 200
    data = response.json()
    assert data["election_id"] == 1
    assert data["alert_type"] == "anomaly"
    assert data["message"] == "Test alert created via POST"
    assert data["status"] == "new"
    # Check that "created_at" exists & is a string timestamp.
    assert "created_at" in data

# ---------------------------------------------------------------------------
# Test PUT /alerts/{alert_id} Endpoint
# ---------------------------------------------------------------------------
def test_update_alert_success(client, test_db, create_test_election, create_test_alert):
    """
    PUT /alerts/{alert_id} should update an alert.
    """
        # Create an alert to update.
    create_test_election(id=1, name="Election Four")
    alert = create_test_alert(election_id=1, alert_type="anomaly", message="Alert to be updated", status="new")
    
    # Prepare the update payload. In our endpoint, the request expects the UpdateAlertCommand.
    # We'll send the new status in JSON.
    update_payload = {
        "alert_id": 1,
        "status": "resolved"   # We want to mark the alert as resolved.
    }
    
    response = client.put(f"/alerts/1", json=update_payload)

    gc.collect()
    test_db.rollback()

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["status"] == "resolved"