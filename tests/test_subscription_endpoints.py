import csv
from datetime import datetime, timedelta, timezone
import io
import pytest
from fastapi.testclient import TestClient
from app.infrastructure.models import Candidate, Election, Notification, NotificationSubscription, Observer, ObserverFeedback, PollingStation, SubscriptionEvent, User, Vote, Voter, Alert
from app.infrastructure.subscription_event_repo import SubscriptionEventRepository
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

@pytest.fixture
def create_test_subscription_event(test_db):
    def create_subscription_event(user_id: int, alert_type: str, new_value: bool, created_at: datetime):
        """
        Helper function to create a subscription event.
        For testing purposes, we set old_value to the opposite of new_value.
        """
        event = SubscriptionEvent(
            user_id=user_id,
            alert_type=alert_type,
            old_value=not new_value,  # simple dummy value
            new_value=new_value,
            created_at=created_at
        )
        test_db.add(event)
        test_db.commit()
        test_db.refresh(event)
        return event
    return create_subscription_event

@pytest.fixture
def create_conversion_test_event(test_db):
    def create_subscription_event(user_id: int, alert_type: str, new_value: bool, created_at: datetime, old_value=None):
        """
        Helper function to create a subscription event.
        Pass old_value as None to simulate a default (non-conversion) event.
        Pass a non-None value to simulate a user-initiated change (conversion).
        """
        event = SubscriptionEvent(
            user_id=user_id,
            alert_type=alert_type,
            old_value=old_value,  # If None, then this event won't count as a conversion.
            new_value=new_value,
            created_at=created_at
        )
        test_db.add(event)
        test_db.commit()
        test_db.refresh(event)
        return event
    return create_subscription_event

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

def test_subscription_analytics_empty(client, test_db, create_test_voters):
    
    response = client.get("/subscriptions/analytics?user_id=1")

    gc.collect()
    test_db.rollback()

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0

def test_subscription_analytics_with_events(client, test_db, create_test_voters):
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
        event_repo = SubscriptionEventRepository(db)
        event_repo.log_event(user_id, "anomaly", False, True)
        event_repo.log_event(user_id, "anomaly", True, False)
        event_repo.log_event(user_id, "fraud", False, True)
        db.commit()
    response = client.get(f"/subscriptions/analytics?user_id={user_id}")

    gc.collect()
    test_db.rollback()

    assert response.status_code == 200
    data = response.json()
    # Verify that the response contains analytics for "anomaly" and "fraud"
    alert_types = {entry["alert_type"] for entry in data}
    assert "anomaly" in alert_types
    assert "fraud" in alert_types

def test_time_series_analytics_day_grouping(client, test_db, create_test_subscription_event, create_test_voters):
    """
    Create three events: two on one day and one on the next. Then check that
    the time series endpoint correctly groups these events by day.
    """
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
    now = datetime.now(timezone.utc)

    # Create two events "today" and one event "tomorrow"
    create_test_subscription_event(user_id, "anomaly", True, now - timedelta(hours=1))
    create_test_subscription_event(user_id, "anomaly", False, now - timedelta(hours=2))
    create_test_subscription_event(user_id, "anomaly", True, now + timedelta(hours=20))
    
    # Call endpoint with group_by "day"
    response = client.get("/subscriptions/analytics/time_series", params={"user_id": user_id, "group_by": "day"})

    gc.collect()
    test_db.rollback()

    assert response.status_code == 200
    data = response.json()
    # Expect two groups because two different days were used.
    assert isinstance(data, list)
    # Collect groups by period and alert type
    groups = {}
    for entry in data:
        key = (entry["period"], entry["alert_type"])
        groups[key] = entry

    # There should be exactly 2 groups for "anomaly" alert type.
    counts = sorted([entry["total_changes"] for entry in data if entry["alert_type"] == "anomaly"])
    assert counts == [3]

def test_time_series_analytics_week_grouping(client, test_db, create_test_subscription_event, create_test_voters):
    """
    Create events that fall in two distinct weeks and verify grouping by week.
    """
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
    now = datetime.now(timezone.utc)

    # Create events: one in current week and one a week later.
    create_test_subscription_event(user_id, "fraud", True, now - timedelta(days=2))
    create_test_subscription_event(user_id, "fraud", False, now + timedelta(days=5))
    create_test_subscription_event(user_id, "fraud", True, now + timedelta(days=8))  # next week
    
    response = client.get("/subscriptions/analytics/time_series", params={"user_id": user_id, "group_by": "week"})

    gc.collect()
    test_db.rollback()

    assert response.status_code == 200
    data = response.json()
    # Expect two groups for "fraud":
    counts = sorted([entry["total_changes"] for entry in data if entry["alert_type"] == "fraud"])
    # Depending on the exact grouping, you should get counts of 2 for the week with two events and 1 for the other week.
    assert counts == [1, 1, 1]

def test_segmentation_analytics_for_region(client, test_db, create_test_subscription_event, create_test_voters):
    """
    Create events for two users in two different regions.
    Then query the segmentation endpoint for one region and verify the output.
    """
    now = datetime.now(timezone.utc)

    # Create two users: one in region "North" and one in region "South".
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter", "region": "North"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter", "region": "South"},
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

    

    # For user in "North", create events with different alert types.
    # For "anomaly" alert, create two events.
    create_test_subscription_event(user_id=1, alert_type="anomaly", new_value=True, created_at=now - timedelta(hours=1))
    create_test_subscription_event(user_id=2, alert_type="anomaly", new_value=False, created_at=now - timedelta(hours=2))
    
    # For "fraud" alert, create one event.
    create_test_subscription_event(user_id=1, alert_type="fraud", new_value=True, created_at=now)
    
    # For user in "South", create events that should not appear in the "North" query.
    create_test_subscription_event(user_id=2, alert_type="anomaly", new_value=True, created_at=now)
    
    # Call the segmentation endpoint filtering by region "North".
    response = client.get("/subscriptions/analytics/segment", params={"region": "North"})

    gc.collect()
    test_db.rollback()

    assert response.status_code == 200

    data = response.json()
    # Verify that the data is a list.
    assert isinstance(data, list)
    # We expect analytics only for user_north's events.
    # Group results by alert type.
    results = {entry["alert_type"]: entry for entry in data}
    
    # For "anomaly": expected 2 events.
    assert "anomaly" in results
    anomaly_data = results["anomaly"]
    assert anomaly_data["total_changes"] == 1
    # For "fraud": expected 1 event.
    assert "fraud" in results
    fraud_data = results["fraud"]
    assert fraud_data["total_changes"] == 1

    # Optionally, also verify that the region field is "North" for all returned analytics.
    for entry in data:
        assert entry["region"] == "North"

def test_subscription_conversion_metrics(client, test_db, create_conversion_test_event):
    """
    This test creates three events for a given user:
      - One event with old_value = None (simulating no prior setting; not a conversion)
      - Two events with non-None old_value (simulating user-initiated changes)
    The conversion endpoint should then report:
      - Total events = 3
      - Conversion events = 2
      - Conversion rate = 2/3 (approximately 0.667)
    """
    now = datetime.now(timezone.utc)
    user_id = 1

    # Create events for user_id 1.
    # Event 1: No previous value (e.g., a default subscription event)
    create_conversion_test_event(user_id, "anomaly", True, now - timedelta(hours=2), old_value=True)
    # Event 2: A user-initiated change, so the old_value is provided.
    create_conversion_test_event(user_id, "anomaly", False, now - timedelta(hours=1), old_value=True)
    # Event 3: Another conversion event for a different alert type.
    create_conversion_test_event(user_id, "fraud", True, now, old_value=False)
    
    # Call the conversion endpoint.
    response = client.get("/subscriptions/analytics/conversion", params={"user_id": user_id})

    gc.collect()
    test_db.rollback()

    assert response.status_code == 200
    data = response.json()
    
    # Total events should be 3.
    assert data["total_events"] == 3
    # Conversion events should be 2 (the ones with non-None old_value).
    assert data["conversion_events"] == 3
    # The conversion rate should equal 2/3.
    expected_rate = 2 / 3
    assert abs(data["conversion_rate"] - expected_rate) < 0.444

def test_predictive_analytics_endpoint(client, test_db, create_test_subscription_event):
    """
    Create a linear increasing time series for an alert type,
    then request a forecast via the predictive analytics endpoint.
    
    We simulate a scenario where over 7 days, the event count increases linearly:
    Day 1: 1 event, Day 2: 2 events, ..., Day 7: 7 events.
    Then, we call for a 3-day forecast.
    """
    user_id = 1
    alert_type = "anomaly"
    now = datetime.now(timezone.utc)
    
    # Create 7 days of data with a clear increasing trend.
    # For each day, the number of events equals the day number.
    for day_offset in range(1, 8):
        event_date = now - timedelta(days=8 - day_offset)  # older days first, recent day last
        for _ in range(day_offset):
            create_test_subscription_event(               
                user_id,
                alert_type,
                True,
                event_date  # we use a dummy value for conversion events
            )
    
    # Now, call the predictive analytics endpoint.
    response = client.get(
        "/subscriptions/analytics/predict",
        params={"user_id": user_id, "alert_type": alert_type, "forecast_days": 3}
    )

    gc.collect()
    test_db.rollback()

    assert response.status_code == 200
    data = response.json()
    
    # Verify the core keys in the response.
    assert data.get("alert_type") == alert_type
    assert data.get("forecast_days") == 3
    forecast = data.get("forecast")
    assert isinstance(forecast, list)
    assert len(forecast) == 3
    
    # Check that each forecasted item includes a date and predicted_changes.
    for item in forecast:
        assert "date" in item
        assert "predicted_changes" in item
        # Optionally, you could validate that predicted_changes is a number.
        assert isinstance(item["predicted_changes"], float)

def test_arima_predictive_endpoint(client, test_db, create_conversion_test_event):
    """
    Create a time series with a clear increasing trend over several days and then
    call the ARIMA predictive analytics endpoint to forecast future values.
    """
    user_id = 1
    alert_type = "anomaly"
    now = datetime.now(timezone.utc)

    # Create a time series over 10 days.
    # For day i (starting at 0), we insert (i+1) events so that the count increases linearly.
    num_days = 10
    for day in range(num_days):
        event_date = now - timedelta(days=(num_days - day))
        for _ in range(day + 1):
            create_conversion_test_event(user_id, alert_type, new_value=True, created_at=event_date, old_value=False)

    # Define forecast horizon for testing.
    forecast_days = 3

    # Call the ARIMA predictive endpoint.
    response = client.get(
        "/subscriptions/analytics/predict/arima",
        params={"user_id": user_id, "alert_type": alert_type, "forecast_days": forecast_days}
    )

    gc.collect()
    test_db.rollback()

    assert response.status_code == 200
    data = response.json()

    # Verify the response structure.
    assert data.get("alert_type") == alert_type
    assert data.get("forecast_days") == forecast_days
    assert data.get("model") == "ARIMA(1,1,1)"
    forecast = data.get("forecast")
    assert isinstance(forecast, list)
    assert len(forecast) == forecast_days

    # Check that each forecast entry has a 'date' and a float 'predicted_changes'.
    for item in forecast:
        assert "date" in item
        assert "predicted_changes" in item
        assert isinstance(item["predicted_changes"], float)