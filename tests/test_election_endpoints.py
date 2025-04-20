import pytest
from fastapi.testclient import TestClient
from app.main import app  # Import the FastAPI instance from main.py
from app.infrastructure.database import SessionLocal, Base, engine


# Use a fresh test database
@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    # Create tables for the test database
    Base.metadata.create_all(bind=engine)
    yield
    # Drop all tables after the test
    Base.metadata.drop_all(bind=engine)

# Initialize TestClient for the FastAPI app
client = TestClient(app)

def test_create_election():
    response = client.post(
        "/elections/elections/new",
        json={
            "name": "Presidential Election",
            "candidates": ["Alice", "Bob", "Charlie"]
        },
    )
    print("Response JSON:", response.json())  # Debugging output
    assert response.status_code == 200
    assert "election_id" in response.json()

def test_get_election_details():
    # First, create an election
    create_response = client.post(
        "/elections/elections/new",
        json={
            "name": "Presidential Election",
            "candidates": ["Alice", "Bob", "Charlie"]
        },
    )
    election_id = create_response.json()["election_id"]

    # Fetch the election details
    response = client.get(f"/elections/elections/{election_id}/")
    assert response.status_code == 200
    data = response.json()
    assert data["election_id"] == election_id
    assert data["name"] == "Presidential Election"
    assert data["candidates"] == ["Alice", "Bob", "Charlie"]
    assert data["votes"] == [0, 0, 0]

def test_list_all_elections():
    # Create multiple elections
    client.post(
        "/elections/elections/new",
        json={
            "name": "Election 1",
            "candidates": ["Candidate 1", "Candidate 2"]
        },
    )
    client.post(
        "/elections/elections/new",
        json={
            "name": "Election 2",
            "candidates": ["Candidate A", "Candidate B"]
        },
    )

    # List all elections
    response = client.get("/elections/elections/")
    print("Response JSON:", response.json())
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Election 1"
    assert data[1]["name"] == "Election 2"

def test_end_election():
    # Create an election
    create_response = client.post(
        "/elections/elections/new",
        json={
            "name": "Election to End",
            "candidates": ["Ender", "Closer"]
        },
    )
    election_id = create_response.json()["election_id"]

    # End the election
    end_response = client.put(f"/elections/elections/{election_id}/end/")
    assert end_response.status_code == 200
    assert end_response.json()["message"] == f"Election {election_id} has been ended successfully."

    # Verify the status has been updated
    get_response = client.get(f"/elections/elections/{election_id}/")
    assert get_response.status_code == 200

def test_get_election_results():
    # Create an election
    create_response = client.post(
        "/elections/elections/new",
        json={
            "name": "Presidential Election",
            "candidates": ["Alice", "Bob", "Charlie"]
        },
    )
    election_id = create_response.json()["election_id"]

    # Fetch the election results
    response = client.get(f"/elections/elections/{election_id}/results/")
    assert response.status_code == 200
    data = response.json()
    print(data)
    assert data == {'Alice': 0, 'Bob': 0, 'Charlie': 0} 
