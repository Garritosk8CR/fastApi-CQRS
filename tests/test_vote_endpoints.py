import pytest
from fastapi.testclient import TestClient
from app.main import app  # Import the FastAPI instance from main.py
from app.infrastructure.database import Base, engine

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

def test_cast_vote():
    # Step 1: Create an election
    create_response = client.post(
        "/elections/",
        json={
            "name": "Presidential Election",
            "candidates": ["Alice", "Bob", "Charlie"]
        },
    )
    assert create_response.status_code == 200
    election_id = create_response.json()["election_id"]

    # Step 2: Register a voter
    register_response = client.post(
        "/voters/",
        json={
            "voter_id": 1,
            "name": "John Doe"
        },
    )
    assert register_response.status_code == 200

    # Step 3: Cast a vote
    vote_response = client.post(
        f"/voters/1/vote/",
        json={"candidate": "Alice"}
    )
    assert vote_response.status_code == 200
    assert vote_response.json()["message"] == "Vote cast successfully for Alice"

def test_cast_vote_voter_already_voted():
    # Step 1: Create an election
    create_response = client.post(
        "/elections/",
        json={
            "name": "Presidential Election",
            "candidates": ["Alice", "Bob", "Charlie"]
        },
    )
    election_id = create_response.json()["election_id"]

    # Step 2: Register a voter
    register_response = client.post(
        "/voters/",
        json={
            "voter_id": 1,
            "name": "John Doe"
        },
    )
    assert register_response.status_code == 200

    # Step 3: Cast the first vote
    client.post(
        f"/voters/1/vote/",
        json={"candidate": "Alice"}
    )

    # Step 4: Attempt to cast another vote for the same voter
    vote_response = client.post(
        f"/voters/1/vote/",
        json={"candidate": "Bob"}
    )
    assert vote_response.status_code == 400
    assert vote_response.json()["detail"] == "Voter has already voted"

def test_cast_vote_invalid_candidate():
    # Step 1: Create an election
    create_response = client.post(
        "/elections/",
        json={
            "name": "Presidential Election",
            "candidates": ["Alice", "Bob", "Charlie"]
        },
    )
    election_id = create_response.json()["election_id"]

    # Step 2: Register a voter
    register_response = client.post(
        "/voters/",
        json={
            "voter_id": 1,
            "name": "John Doe"
        },
    )
    assert register_response.status_code == 200

    # Step 3: Attempt to cast a vote for an invalid candidate
    vote_response = client.post(
        f"/voters/1/vote/",
        json={"candidate": "InvalidCandidate"}
    )
    assert vote_response.status_code == 400
    assert vote_response.json()["detail"] == "Candidate not found"

def test_vote_results():
    # Step 1: Create an election
    create_response = client.post(
        "/elections/",
        json={
            "name": "Presidential Election",
            "candidates": ["Alice", "Bob", "Charlie"]
        },
    )
    election_id = create_response.json()["election_id"]

    # Step 2: Register voters and cast votes
    client.post(
        "/voters/",
        json={"voter_id": 1, "name": "John Doe"}
    )
    client.post(
        "/voters/",
        json={"voter_id": 2, "name": "Jane Smith"}
    )
    client.post(
        f"/voters/1/vote/",
        json={"candidate": "Alice"}
    )
    client.post(
        f"/voters/2/vote/",
        json={"candidate": "Bob"}
    )

    # Step 3: Fetch election results
    results_response = client.get(f"/elections/{election_id}/results/")
    assert results_response.status_code == 200
    results = results_response.json()["results"]
    assert results == {"Alice": 1, "Bob": 1, "Charlie": 0}
