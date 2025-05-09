import datetime
import pytest
from fastapi.testclient import TestClient
from app.infrastructure.models import AuditLog, Election, Observer, PollingStation, User, Voter
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

def test_create_observer(test_db, create_test_elections, client):
    # Arrange: Create an election before adding observers
    elections_data = [{"id": 1, "name": "Presidential Election"}]
    create_test_elections(elections_data)

    request_data = {
        "name": "Observer One",
        "email": "observer1@example.com",
        "election_id": 1,
        "organization": "Transparency Group"
    }

    # Act: Call the endpoint
    response = client.post("/observers", json=request_data)

    # Assert: Verify creation
    print(response.json())
    assert response.status_code == 200
    assert response.json()["name"] == "Observer One"
    assert response.json()["organization"] == "Transparency Group"

    test_db.rollback()
    gc.collect()