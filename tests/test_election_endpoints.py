import gc
import pytest
from fastapi.testclient import TestClient
from app.infrastructure.models import Election
from app.main import app  # Import the FastAPI instance from main.py
from app.infrastructure.database import SessionLocal, Base, engine


@pytest.fixture(scope="module")
def test_db():
    # Ensure the database schema is created
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    yield db
    # Tear down the database after tests
    db.close()
    Base.metadata.drop_all(bind=engine)
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

def test_candidate_support_multiple_candidates(test_db, create_test_elections):
    # Arrange: Create an election with multiple candidates and votes
    elections_data = [
        {
            "id": 1,
            "name": "Election 1",
            "candidates": "Candidate A,Candidate B,Candidate C",
            "votes": "150,200,120"
        }
    ]
    create_test_elections(elections_data)

    # Act: Call the endpoint for the election
    response = client.get("/elections/1/candidate-support")

    # Assert: Verify the response
    assert response.status_code == 200
    assert response.json() == {
        "candidates": [
            {"candidate_name": "Candidate A", "votes": 150},
            {"candidate_name": "Candidate B", "votes": 200},
            {"candidate_name": "Candidate C", "votes": 120}
        ]
    }

    test_db.rollback()
    gc.collect()

def test_candidate_support_election_not_found(test_db):
    # Act: Call the endpoint for a non-existent election
    response = client.get("/elections/999/candidate-support")

    # Assert: Verify the response
    assert response.status_code == 404
    assert response.json() == {"detail": "Election with ID 999 not found."}

    test_db.rollback()
    gc.collect()

def test_candidate_support_no_votes(test_db, create_test_elections):
    # Arrange: Create an election with candidates but no votes
    elections_data = [
        {
            "id": 2,
            "name": "Election 2",
            "candidates": "Candidate X,Candidate Y,Candidate Z",
            "votes": "0,0,0"
        }
    ]
    create_test_elections(elections_data)

    # Act: Call the endpoint for the election
    response = client.get("/elections/2/candidate-support")

    # Assert: Verify the response
    assert response.status_code == 200
    assert response.json() == {
        "candidates": [
            {"candidate_name": "Candidate X", "votes": 0},
            {"candidate_name": "Candidate Y", "votes": 0},
            {"candidate_name": "Candidate Z", "votes": 0}
        ]
    }

    test_db.rollback()
    gc.collect()