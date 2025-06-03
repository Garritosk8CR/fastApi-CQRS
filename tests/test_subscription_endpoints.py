import csv
from datetime import datetime, timedelta, timezone
import io
import pytest
from fastapi.testclient import TestClient
from app.infrastructure.models import Candidate, Election, Notification, NotificationSubscription, Observer, ObserverFeedback, PollingStation, User, Vote, Voter, Alert
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

# Test for GET /subscriptions when no subscriptions exist.
def test_get_subscriptions_empty(client, test_db, create_test_voters):
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
    # Assume user_id 1 exists (or we simply use a number).
    response = client.get("/subscriptions?user_id=1")


    gc.collect()
    test_db.rollback()

    assert response.status_code == 200
    data = response.json()
    # When no subscriptions exist for the user, expect an empty list.
    assert isinstance(data, list)
    assert len(data) == 0

def test_update_subscription_creates(client, test_db, create_test_voters):
    user_id = 1
    alert_type = "anomaly"
    is_subscribed = False
    
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
    # Optionally, create a test user if required.
    

    response = client.put(f"/subscriptions?user_id={user_id}&alert_type={alert_type}&is_subscribed={str(is_subscribed).lower()}")

    gc.collect()
    test_db.rollback()

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user_id
    assert data["alert_type"] == alert_type
    assert data["is_subscribed"] == is_subscribed

# Test update subscription to modify an existing record.
def test_update_subscription_modifies(client, test_db, create_test_voters):
    user_id = 1
    alert_type = "fraud"
    
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

    with SessionLocal() as db:
        # Create an initial subscription with is_subscribed = True.
        sub = NotificationSubscription(
            user_id=user_id,
            alert_type=alert_type,
            is_subscribed=True,
            created_at=datetime.now(timezone.utc)
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
    
    # Now update the subscription to is_subscribed = False.
    response = client.put(f"/subscriptions?user_id={user_id}&alert_type={alert_type}&is_subscribed=false")

    gc.collect()
    test_db.rollback()
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user_id
    assert data["alert_type"] == alert_type
    assert data["is_subscribed"] is False

# ---------------------------------------------------------------------------
# Test Bulk Update /subscriptions/bulk Endpoint for Creating New Subscriptions.
# ---------------------------------------------------------------------------
def test_bulk_update_subscription_creates(client, test_db, create_test_voters):
    user_id = 1
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
    payload = {
        "user_id": user_id,
        "updates": [
            {"alert_type": "anomaly", "is_subscribed": True},
            {"alert_type": "fraud", "is_subscribed": False},
            {"alert_type": "system", "is_subscribed": True}
        ]
    }
    response = client.put("/subscriptions/bulk", json=payload)

    gc.collect()
    test_db.rollback()

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3

    for sub in data:
        if sub["alert_type"] == "fraud":
            assert sub["is_subscribed"] is False
        elif sub["alert_type"] in ["anomaly", "system"]:
            assert sub["is_subscribed"] is True

# ---------------------------------------------------------------------------
# Test Bulk Update to Modify Existing Subscriptions.
# ---------------------------------------------------------------------------
def test_bulk_update_subscription_modifies(client, test_db, create_test_voters):
    user_id = 1
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
    with SessionLocal() as db:
        # Create initial subscriptions for user1.
        sub1 = NotificationSubscription(user_id=user_id, alert_type="anomaly", is_subscribed=True)
        sub2 = NotificationSubscription(user_id=user_id, alert_type="fraud", is_subscribed=True)
        db.add(sub1)
        db.add(sub2)
        db.commit()
    
    payload = {
        "user_id": user_id,
        "updates": [
            {"alert_type": "anomaly", "is_subscribed": False},
            {"alert_type": "fraud", "is_subscribed": False},
        ]
    }
    response = client.put("/subscriptions/bulk", json=payload)

    gc.collect()
    test_db.rollback()

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    for sub in data:
        if sub["alert_type"] == "anomaly":
            assert sub["is_subscribed"] is False
        elif sub["alert_type"] == "fraud":
            assert sub["is_subscribed"] is False

# ---------------------------------------------------------------------------
# Test WebSocket Endpoint for Subscriptions
# ---------------------------------------------------------------------------
def test_subscriptions_websocket(client, test_db, create_test_voters):
    user_id = 1
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
    with SessionLocal() as db:
        sub = NotificationSubscription(user_id=user_id, alert_type="anomaly", is_subscribed=True)
        db.add(sub)
        db.commit()
        db.refresh(sub)
    
    # Connect to the subscriptions WebSocket endpoint.
    with client.websocket_connect(f"subscriptions/ws?user_id={user_id}") as websocket:
        data = websocket.receive_json()

        gc.collect()
        test_db.rollback()

        assert isinstance(data, list)
        # Verify that at least one subscription (anomaly) is present.
        found = any(s.get("alert_type") == "anomaly" for s in data)
        assert found

def test_realtime_subscription_update(client, test_db, create_test_voters):
    user_id = 1
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
    # Assume a test user exists; if not, it’s enough to use the user_id.
    # Connect to the WebSocket endpoint.
    with client.websocket_connect(f"/subscriptions/ws?user_id={user_id}") as websocket:
        # Initially, the WebSocket sends the current state (could be empty).
        initial_data = websocket.receive_json()
        # Now perform a bulk update for this user.
        payload = {
            "user_id": user_id,
            "updates": [
                {"alert_type": "anomaly", "is_subscribed": True},
                {"alert_type": "fraud", "is_subscribed": False}
            ]
        }
        response = client.put("/subscriptions/bulk", json=payload)
        assert response.status_code == 200
        # The update call should trigger a broadcast.
        updated_msg = websocket.receive_json()

        gc.collect()
        test_db.rollback()
        # Expect the broadcast message to contain the updated subscriptions.
        assert "subscriptions" in updated_msg
        subs = updated_msg["subscriptions"]
        assert any(s["alert_type"] == "fraud" and s["is_subscribed"] is False for s in subs)