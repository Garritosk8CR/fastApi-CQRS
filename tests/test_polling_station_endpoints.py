import pytest
from fastapi.testclient import TestClient
from app.infrastructure.models import Election, PollingStation, User, Voter
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

def test_create_polling_station(test_db, create_test_elections, client):
    # Arrange: Create an election before adding polling stations
    elections_data = [{"id": 1, "name": "Presidential Election"}]
    create_test_elections(elections_data)

    request_data = {
        "name": "Central Voting Station",
        "location": "City Hall",
        "election_id": 1,
        "capacity": 500
    }

    # Act: Call the endpoint
    response = client.post("/polling-stations/add", json=request_data)

    # Assert: Verify creation
    print(f"Polling station response: {response.json()}")
    assert response.status_code == 200
    assert response.json()["name"] == "Central Voting Station"
    assert response.json()["location"] == "City Hall"
    
    test_db.rollback()
    gc.collect()

def test_get_polling_station_by_id(test_db, create_test_polling_stations, client, create_test_elections):

    elections_data = [{"id": 1, "name": "Presidential Election"}]
    create_test_elections(elections_data)
    # Arrange: Create polling stations
    stations_data = [
        {"id": 1, "name": "North Polling", "location": "School", "election_id": 1, "capacity": 300}
    ]

    create_test_polling_stations(stations_data)

    # Act: Call the endpoint
    response = client.get("/polling-stations/1")

    # Assert: Verify retrieval
    assert response.status_code == 200
    assert response.json()["name"] == "North Polling"

def test_get_polling_stations_by_election(test_db, create_test_polling_stations, create_test_elections, client):

    elections_data = [{"id": 1, "name": "Presidential Election"}]
    create_test_elections(elections_data)
    # Arrange: Create polling stations for an election
    stations_data = [
        {"id": 1, "name": "North Polling", "location": "School", "election_id": 1, "capacity": 300},
        {"id": 2, "name": "South Polling", "location": "Community Center", "election_id": 1, "capacity": 400},
    ]
    create_test_polling_stations(stations_data)

    # Act: Call the endpoint
    response = client.get("/polling-stations/elections/1/polling-stations")

    # Assert: Verify correct filtering
    assert response.status_code == 200
    assert len(response.json()) == 2

    test_db.rollback()
    gc.collect()

def test_update_polling_station(test_db, create_test_polling_stations, create_test_elections, client):

    elections_data = [{"id": 1, "name": "Presidential Election"}]
    create_test_elections(elections_data)
    # Arrange: Create a polling station
    stations_data = [
        {"id": 1, "name": "East Polling", "location": "Library", "election_id": 1, "capacity": 250}
    ]
    create_test_polling_stations(stations_data)

    update_data = {
        "station_id": 1,
        "name": "Updated Polling Station",
        "location": "Conference Hall",
        "capacity": 600
    }

    # Act: Call the endpoint
    response = client.patch("/polling-stations/1", json=update_data)

    # Assert: Verify update
    print(f"Polling station response: {response.json()}")
    assert response.status_code == 200

    test_db.rollback()
    gc.collect()

def test_delete_polling_station(test_db, create_test_polling_stations, create_test_elections, client):

    elections_data = [{"id": 1, "name": "Presidential Election"}]
    create_test_elections(elections_data)
    # Arrange: Create a polling station
    stations_data = [
        {"id": 1, "name": "West Polling", "location": "Gym", "election_id": 1, "capacity": 200}
    ]
    create_test_polling_stations(stations_data)

    # Act: Call the endpoint
    response = client.delete("/polling-stations/1")

    # Assert: Verify deletion
    assert response.status_code == 200
    assert response.json()["message"] == "Polling station deleted successfully"