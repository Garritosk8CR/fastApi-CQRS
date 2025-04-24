import pytest
from fastapi.testclient import TestClient
from app.infrastructure.models import User, Voter
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

def test_cast_vote(client, test_db):
    # Step 1: Create an election
    create_response = client.post(
        "/elections/elections/new",
        json={
            "name": "Presidential Election",
            "candidates": ["Alice", "Bob", "Charlie"]
        },
    )
    assert create_response.status_code == 200
    election_id = create_response.json()["election_id"]

    # Step 2: Register a voter
    register_response = client.post(
        "/voters/voters",
        json={
            "voter_id": 1,
            "name": "John Doe",
            "email": "john.doe@example.com",
            "password": "password123"
        },
    )
    print(f"Voter registered: {register_response.json()} \n\n")
    assert register_response.status_code == 200
    print(f"Voter registered: {register_response.json()} \n\n")
    # Step 3: Cast a vote
    vote_response = client.post(
        f"/voters/voters/1/elections/{election_id}/cast_vote/",
        json={         
            "voter_id": 1,
            "election_id": election_id,
            "candidate": "Alice"          
            }
    )
    assert vote_response.status_code == 200
    assert vote_response.json()["message"] == "Vote cast successfully for Alice"
    test_db.rollback()
    gc.collect()

def test_cast_vote_voter_already_voted(client, test_db):
    # Step 1: Create an election
    create_response = client.post(
        "/elections/elections/new",
        json={
            "name": "Presidential Election",
            "candidates": ["Alice", "Bob", "Charlie"]
        },
    )
    assert create_response.status_code == 200
    election_id = create_response.json()["election_id"]

    # Step 2: Register a voter
    register_response = client.post(
        "/voters/voters",
        json={
            "voter_id": 1,
            "name": "John Doe",
            "email": "john.doe@example.com",
            "password": "password123"
        },
    )
    assert register_response.status_code == 200

    # Step 3: Cast the first vote
    client.post(
        f"/voters/voters/1/elections/{election_id}/cast_vote/",
        json={
            "voter_id": 1,
            "election_id": election_id,
            "candidate": "Alice"
            }
    )

    # Step 4: Attempt to cast another vote for the same voter
    vote_response = client.post(
        f"/voters/voters/1/elections/{election_id}/cast_vote/",
        json={
            "voter_id": 1,
            "election_id": election_id,
            "candidate": "Bob"
            }
    )
    assert vote_response.status_code == 400
    assert vote_response.json()["detail"] == "Voter has already voted"
    test_db.rollback()
    gc.collect()

def test_cast_vote_invalid_candidate(client, test_db):
    # Step 1: Create an election
    create_response = client.post(
        "/elections/elections/new",
        json={
            "name": "Presidential Election",
            "candidates": ["Alice", "Bob", "Charlie"]
        },
    )
    assert create_response.status_code == 200
    election_id = create_response.json()["election_id"]

    # Step 2: Register a voter
    register_response = client.post(
        "/voters/voters",
        json={
            "voter_id": 1,
            "name": "John Doe",
            "email": "john.doe@example.com",
            "password": "password123"
        },
    )
    assert register_response.status_code == 200

    # Step 3: Attempt to cast a vote for an invalid candidate
    vote_response = client.post(
        f"/voters/voters/1/elections/{election_id}/cast_vote/",
        json={
            "voter_id": 1,
            "election_id": election_id,
            "candidate": "InvalidCandidate"
            }
    )
    assert vote_response.status_code == 400
    assert vote_response.json()["detail"] == "Candidate not found"
    test_db.rollback()
    gc.collect()

def test_vote_results(client, test_db):
    # Step 1: Create an election
    create_response = client.post(
        "/elections/elections/new",
        json={
            "name": "Presidential Election",
            "candidates": ["Alice", "Bob", "Charlie"]
        },
    )
    print(create_response.json())
    assert create_response.status_code == 200
    print(create_response.json())
    election_id = create_response.json()["election_id"]

    # Step 2: Register voters and cast votes
    client.post(
        "/voters/voters",
        json={"voter_id": 1, "name": "John Doe", "email": "john.doe@example.com", "password": "password123"  },
    )
    client.post(
        "/voters/voters",
        json={"voter_id": 2, "name": "Jane Smith", "email": "jane.smith@example.com", "password": "password456"  },
    )
    client.post(
        f"/voters/voters/1/elections/{election_id}/cast_vote/",
        json={
            "voter_id": 1,
            "election_id": election_id,
            "candidate": "Alice"
        }
    )
    client.post(
        f"/voters/voters/2/elections/{election_id}/cast_vote/",
        json={
            "voter_id": 2,
            "election_id": election_id,
            "candidate": "Bob"
        }
    )

    # Step 3: Fetch election results
    results_response = client.get(f"/elections/elections/{election_id}/results/")
    assert results_response.status_code == 200
    results = results_response.json()
    assert results == {"Alice": 1, "Bob": 1, "Charlie": 0}
    test_db.rollback()
    gc.collect()

def test_user_has_voted(test_db, create_test_user_and_voter, client):
    # Arrange: Create a user who has voted
    user, voter = create_test_user_and_voter(10, "Test User", "test10@example.com", True)

    # Act: Call the has-voted endpoint
    response = client.get(f"/voters/users/{user.id}/has-voted")

    # Assert: Verify the response
    print(response.json())
    assert response.status_code == 200
    assert response.json() == {"user_id": user.id, "has_voted": True}
    test_db.rollback()
    gc.collect()