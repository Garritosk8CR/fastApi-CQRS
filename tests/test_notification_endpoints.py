import csv
from datetime import datetime, timedelta, timezone
import io
import pytest
from fastapi.testclient import TestClient
from app.infrastructure.models import Candidate, Election, Notification, Observer, ObserverFeedback, PollingStation, User, Vote, Voter, Alert
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

@pytest.fixture
def create_test_notification(test_db):
    def create_notification(alert_id: int, user_id: int, message: str, is_read: bool = False):
        notification = Notification(
            alert_id=alert_id,
            user_id=user_id,
            message=message,
            is_read=is_read,
            created_at=datetime.now(timezone.utc)
        )
        test_db.add(notification)
        test_db.commit()
        test_db.refresh(notification)
        return notification
    return create_notification

# ---------------------------------------------------------------------------
# Test GET /notifications Endpoint
# ---------------------------------------------------------------------------
def test_get_notifications_empty(client, test_db, create_test_voters):
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"},
        {"id": 4, "name": "Active Voter 4", "email": "active4@example.com", "role": "voter"},
        {"id": 5, "name": "Active Voter 5", "email": "active5@example.com", "role": "voter"},
        {"id": 6, "name": "Active Voter 6", "email": "active6@example.com", "role": "voter"},
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True},
        {"user_id": 4, "has_voted": True},
        {"user_id": 5, "has_voted": False},
        {"user_id": 6, "has_voted": False}
    ]
    create_test_voters(users_data, voters_data)
    """
    When no notifications exist for a user, GET /notifications should return an empty list.
    """
    response = client.get("/notifications?user_id=1")

    gc.collect()
    test_db.rollback()

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0

def test_get_notifications_returns_results(client, test_db, create_test_voters, create_test_alert, create_test_notification, create_test_election):
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"},
        {"id": 4, "name": "Active Voter 4", "email": "active4@example.com", "role": "voter"},
        {"id": 5, "name": "Active Voter 5", "email": "active5@example.com", "role": "voter"},
        {"id": 6, "name": "Active Voter 6", "email": "active6@example.com", "role": "voter"},
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True},
        {"user_id": 4, "has_voted": True},
        {"user_id": 5, "has_voted": False},
        {"user_id": 6, "has_voted": False}
    ]
    create_test_voters(users_data, voters_data)
    """
    Create a notification for a given user and verify GET /notifications returns it.
    """
    
        # Create a test election and alert (for foreign key integrity).
    election = create_test_election(id=1, name="Test Election")
    alert = create_test_alert(election_id=1, alert_type="anomaly", message="Test alert")
    # Create a notification for user_id 1.
    create_test_notification(alert_id=1, user_id=1, message="This is a test notification")
    
    response = client.get("/notifications?user_id=1")

    gc.collect()
    test_db.rollback()

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    
    notif = data[0]
    assert notif["user_id"] == 1
    assert notif["alert_id"] == 1
    assert notif["message"] == "This is a test notification"
    assert notif["is_read"] is False
    assert "created_at" in notif