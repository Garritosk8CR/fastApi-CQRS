import datetime
import pytest
from fastapi.testclient import TestClient
from app.infrastructure.models import AuditLog, Election, PollingStation, User, Voter
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

@pytest.fixture
def create_test_audit_logs(test_db):
    def _create_logs(logs_data):
        logs = []
        for log_data in logs_data:
            log = AuditLog(**log_data)
            test_db.add(log)
            logs.append(log)
        test_db.commit()
        return logs
    return _create_logs

def test_create_audit_log(test_db, create_test_elections, create_test_users, client):
    # Arrange: Create an election and a user
    elections_data = [{"id": 1, "name": "Presidential Election"}]
    users_data = [{"id": 1, "name": "Admin User", "email": "admin@example.com"}]
    create_test_elections(elections_data)
    create_test_users(users_data)

    request_data = {
        "election_id": 1,
        "performed_by": 1,
        "action": "Added Candidate",
        "details": "Candidate John Doe added"
    }

    # Act: Call the endpoint
    response = client.post("/audit-logs", json=request_data)

    # Assert: Verify log creation
    assert response.status_code == 200
    assert response.json()["action"] == "Added Candidate"
    assert response.json()["details"] == "Candidate John Doe added"

    test_db.rollback()
    gc.collect()

def test_get_audit_logs_by_election(test_db, create_test_audit_logs, client, create_test_elections, create_test_users):
    elections_data = [{"id": 1, "name": "Presidential Election"}]
    users_data = [{"id": 1, "name": "Admin User", "email": "admin@example.com"}, {"id": 2, "name": "Voter User 1", "email": "voter1@example.com"}]
    create_test_elections(elections_data)
    create_test_users(users_data)
    # Arrange: Create audit logs
    logs_data = [
        {"id": 1, "election_id": 1, "performed_by": 1, "action": "Added Candidate", "details": "Candidate A added", "timestamp": datetime.datetime.now(datetime.timezone.utc)},
        {"id": 2, "election_id": 1, "performed_by": 2, "action": "Updated Voter Status", "details": "Marked voter as inactive", "timestamp": datetime.datetime.now(datetime.timezone.utc)},
    ]
    create_test_audit_logs(logs_data)

    # Act: Call the endpoint
    response = client.get("audit-logs/elections/1/audit-logs")

    # Assert: Verify log retrieval
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["action"] == "Added Candidate"