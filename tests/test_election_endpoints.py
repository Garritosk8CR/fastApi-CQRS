import gc
import pytest
from fastapi.testclient import TestClient
from app.infrastructure.models import Election, User, Voter
from app.main import app  # Import the FastAPI instance from main.py
from app.infrastructure.database import SessionLocal, Base, engine
from tests.test_vote_endpoints import create_test_user_and_voter


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

def test_turnout_calculation(test_db, create_test_voters,create_test_elections):

    elections_data = [
        {
            "id": 1,
            "name": "Election 1",
            "candidates": "Candidate X,Candidate Y,Candidate Z",
            "votes": "0,0,0"
        }
    ]
    create_test_elections(elections_data)
    # Arrange: Create users and voters
    users_data = [
        {"id": 1, "name": "User 1", "email": "user1@example.com", "role": "voter"},
        {"id": 2, "name": "User 2", "email": "user2@example.com", "role": "voter"},
        {"id": 3, "name": "User 3", "email": "user3@example.com", "role": "voter"},
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": False},
        {"user_id": 3, "has_voted": True},
    ]
    create_test_voters(users_data, voters_data)

    # Act: Call the endpoint
    response = client.get("/elections/1/turnout")

    # Assert: Verify the turnout calculation
    assert response.status_code == 200
    assert response.json() == {
        "election_id": 1,
        "total_voters": 3,
        "voted": 2,
        "turnout_percentage": 66.67
    }

    test_db.rollback()
    gc.collect()

def test_turnout_election_not_found(test_db):
    # Act: Call the endpoint for a non-existent election
    response = client.get("/elections/999/turnout")

    # Assert: Verify the response
    assert response.status_code == 404
    assert response.json() == {"detail": "Election with ID 999 not found."}

    test_db.rollback()
    gc.collect()

def test_turnout_no_voters(test_db, create_test_elections):

    elections_data = [
        {
            "id": 1,
            "name": "Election 1",
            "candidates": "Candidate X,Candidate Y,Candidate Z",
            "votes": "0,0,0"
        }
    ]
    create_test_elections(elections_data)
    # Act: Call the endpoint when there are no voters
    response = client.get("/elections/1/turnout")

    # Assert: Verify the response
    assert response.status_code == 200
    assert response.json() == {
        "election_id": 1,
        "total_voters": 0,
        "voted": 0,
        "turnout_percentage": 0.0
    }

    test_db.rollback()
    gc.collect()

def test_turnout_no_participation(test_db, create_test_voters, create_test_elections):

    elections_data = [
        {
            "id": 1,
            "name": "Election 1",
            "candidates": "Candidate X,Candidate Y,Candidate Z",
            "votes": "0,0,0"
        }
    ]
    create_test_elections(elections_data)
    # Arrange: Create users who did not vote
    users_data = [
        {"id": 1, "name": "User 1", "email": "user1@example.com", "role": "voter"},
        {"id": 2, "name": "User 2", "email": "user2@example.com", "role": "voter"},
    ]
    voters_data = [
        {"user_id": 1, "has_voted": False},
        {"user_id": 2, "has_voted": False},
    ]
    create_test_voters(users_data, voters_data)

    # Act: Call the endpoint
    response = client.get("/elections/1/turnout")

    # Assert: Verify the turnout calculation
    assert response.status_code == 200
    assert response.json() == {
        "election_id": 1,
        "total_voters": 2,
        "voted": 0,
        "turnout_percentage": 0.0
    }

    test_db.rollback()
    gc.collect()

def test_election_summary_turnout(test_db, create_test_elections, create_test_user_and_voter):
    # Arrange: Create an election with candidates but no votes
    # First, create some voters
    create_test_user_and_voter(user_id=1, name="Test User 1", email="test1@example.com", has_voted=True)
    create_test_user_and_voter(user_id=2, name="Test User 2", email="test2@example.com", has_voted=False)


    elections_data = [
        {
            "id": 1,
            "name": "Election 1",
            "candidates": "Candidate A,Candidate B",
            "votes": "1,1"
        }
    ]
    create_test_elections(elections_data)

    # Act: Call the endpoint for the election
    response = client.get("/elections/summary/")

    # Assert: Verify the response
    assert response.status_code == 200
    summary = response.json()
    assert len(summary) == 1
    print(summary)
    assert summary["elections"][0]["turnout_percentage"] == 50.0
    assert summary["elections"][0]["total_votes"] == 2
    assert summary["elections"][0]["name"] == "Election 1"

    test_db.rollback()
    gc.collect()

def test_election_summary_no_elections(test_db):
    # Act: Call the endpoint when no elections exist
    response = client.get("/elections/summary/")

    # Assert: Verify the response
    assert response.status_code == 200
    assert response.json() == {"elections": []}

    test_db.rollback()
    gc.collect()

def test_election_summary_no_votes(test_db, create_test_elections):
    # Arrange: Create an election with no votes recorded
    elections_data = [
        {"id": 3, "name": "Regional Election", "candidates": "D,E,F", "votes": "0,0,0"},
    ]
    create_test_elections(elections_data)

    # Act: Call the endpoint
    response = client.get("/elections/summary/")

    # Assert: Verify the summary
    assert response.status_code == 200
    assert response.json() == {
        "elections": [
            {"election_id": 3, "name": "Regional Election", "turnout_percentage": 0.0, "total_votes": 0},
        ]
    }

    test_db.rollback()
    gc.collect()

def test_top_candidate_multiple_candidates(test_db, create_test_elections):
    # Arrange: Create an election with multiple candidates and votes
    elections_data = [
        {"id": 1, "name": "Presidential Election", "candidates": "A,B,C", "votes": "100,200,150"}
    ]
    create_test_elections(elections_data)

    # Act: Call the endpoint
    response = client.get("/elections/1/top-candidate/")

    # Assert: Verify the top candidate
    assert response.status_code == 200
    assert response.json() == {
        "election_id": 1,
        "top_candidate": "B",
        "votes": 200
    }

    test_db.rollback()
    gc.collect()

def test_top_candidate_election_not_found(test_db):
    # Act: Call the endpoint for a non-existent election
    response = client.get("/elections/999/top-candidate/")

    # Assert: Verify the response
    assert response.status_code == 404
    assert response.json() == {"detail": "Election with ID 999 not found."}

    test_db.rollback()
    gc.collect()