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

def test_get_observers_by_election(test_db, create_test_observers, create_test_elections, client):

    elections_data = [{"id": 1, "name": "Presidential Election"}]
    create_test_elections(elections_data)
    # Arrange: Create observers linked to an election
    observers_data = [
        {"id": 1, "name": "Observer A", "email": "observerA@example.com", "election_id": 1, "organization": "Group X"},
        {"id": 2, "name": "Observer B", "email": "observerB@example.com", "election_id": 1, "organization": "Group Y"},
    ]
    create_test_observers(observers_data)

    # Act: Call the endpoint
    response = client.get("/observers/elections/1/observers")

    # Assert: Verify correct filtering
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["name"] == "Observer A"

    test_db.rollback()
    gc.collect()

def test_update_observer(test_db, create_test_observers, create_test_elections, client):
    elections_data = [{"id": 1, "name": "Presidential Election"}]
    create_test_elections(elections_data)
    # Arrange: Create an observer
    observers_data = [
        {"id": 1, "name": "Observer C", "email": "observerC@example.com", "election_id": 1, "organization": "Old Org"}
    ]
    create_test_observers(observers_data)

    update_data = {
        "observer_id": 1,
        "name": "Updated Observer",
        "organization": "New Transparency Org"
    }

    # Act: Call the endpoint
    response = client.patch("/observers/1", json=update_data)
    print(response.json())
    # Assert: Verify update
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Observer"
    assert response.json()["organization"] == "New Transparency Org"

    test_db.rollback()
    gc.collect()

def test_delete_observer(test_db, create_test_observers, create_test_elections, client):
    elections_data = [{"id": 1, "name": "Presidential Election"}]
    create_test_elections(elections_data)
    # Arrange: Create an observer
    observers_data = [
        {"id": 1, "name": "Observer D", "email": "observerD@example.com", "election_id": 1, "organization": "Monitoring Org"}
    ]
    create_test_observers(observers_data)

    # Act: Call the endpoint
    response = client.delete("/observers/1")

    # Assert: Verify deletion
    assert response.status_code == 200
    assert response.json()["message"] == "Observer deleted successfully"

    test_db.rollback()
    gc.collect()

# def test_observer_not_found(test_db, client):
#     # Act: Call the endpoint for a non-existent observer
#     response = client.get("/observers/999")

#     # Assert: Verify response handling
#     assert response.status_code == 404
#     assert response.json()["detail"] == "Observer with ID 999 not found."

#     test_db.rollback()
#     gc.collect()

def test_get_observer_by_id_success(test_db, create_test_observers, create_test_elections, client):
    elections_data = [{"id": 1, "name": "Presidential Election"}]
    create_test_elections(elections_data)
    # Arrange: Create an observer
    observers_data = [
        {"id": 1, "name": "Observer X", "email": "observerx@example.com", "election_id": 1, "organization": "Transparency Watch"}
    ]
    create_test_observers(observers_data)

    # Act: Call the endpoint
    response = client.get("/observers/1")

    # Assert: Verify correct retrieval
    assert response.status_code == 200
    assert response.json()["name"] == "Observer X"
    assert response.json()["organization"] == "Transparency Watch"

    test_db.rollback()
    gc.collect()

# def test_get_observer_by_id_not_found(test_db, client):
#     # Act: Call the endpoint for a nonexistent observer
#     response = client.get("/observers/999")

#     # Assert: Verify response handling
#     assert response.status_code == 404
#     assert response.json()["detail"] == "Observer with ID 999 not found."

#     test_db.rollback()
#     gc.collect()