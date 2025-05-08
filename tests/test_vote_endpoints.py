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

def test_user_not_found(test_db, client):
    # Act: Call the has-voted endpoint for a non-existent user
    response = client.get("voters/users/999/has-voted")

    # Assert: Verify the response
    assert response.status_code == 400
    assert response.json() == {"detail": "User with ID 999 not found."}

    test_db.rollback()
    gc.collect()

def test_user_has_not_voted(test_db, create_test_user_and_voter, client):
    # Arrange: Create a user who has not voted
    # user = User(name="Test User", email="test10@example.com", role="voter")
    # test_db.add(user)
    # voter = Voter(user_id=user.id, has_voted=False)
    # test_db.add(voter)
    # test_db.commit()

    # # Act: Call the has-voted endpoint
    # response = client.get(f"/users/{user.id}/has-voted")

    # # Assert: Verify the response
    # assert response.status_code == 200
    # assert response.json() == {"user_id": user.id, "has_voted": False}
    test_db.rollback()
    gc.collect()


@pytest.fixture
def create_test_users_and_voters(test_db):
    def _create_users_and_voters(users_data, voters_data):
        users = []
        voters = []
        
        for user_data in users_data:
            user = User(**user_data)
            test_db.add(user)
            users.append(user)

        test_db.flush()  # Ensure users are added before creating voters
        
        for voter_data in voters_data:
            voter = Voter(**voter_data)
            test_db.add(voter)
            voters.append(voter)
        
        test_db.commit()
        return users, voters
    return _create_users_and_voters

def test_voting_status_both_categories(test_db, create_test_users_and_voters, client):
    # Arrange: Create users and voters in both categories
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
    create_test_users_and_voters(users_data, voters_data)

    # Act: Call the endpoint
    response = client.get("voters/users/voting-status")

    # Assert: Verify the response
    assert response.status_code == 200
    assert response.json() == {
        "voted": [
            {"id": 1, "name": "User 1", "email": "user1@example.com"},
            {"id": 3, "name": "User 3", "email": "user3@example.com"}
        ],
        "not_voted": [
            {"id": 2, "name": "User 2", "email": "user2@example.com"}
        ]
    }

    test_db.rollback()
    gc.collect()

def test_voting_status_all_voted(test_db, create_test_users_and_voters, client):
    # Arrange: Create users who have all voted
    users_data = [
        {"id": 1, "name": "User 1", "email": "user1@example.com", "role": "voter"},
        {"id": 2, "name": "User 2", "email": "user2@example.com", "role": "voter"},
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
    ]
    create_test_users_and_voters(users_data, voters_data)

    # Act: Call the endpoint
    response = client.get("voters/users/voting-status")

    # Assert: Verify the response
    assert response.status_code == 200
    assert response.json() == {
        "voted": [
            {"id": 1, "name": "User 1", "email": "user1@example.com"},
            {"id": 2, "name": "User 2", "email": "user2@example.com"}
        ],
        "not_voted": []
    }

    test_db.rollback()
    gc.collect()

def test_voting_status_all_not_voted(test_db, create_test_users_and_voters, client):
    # Arrange: Create users who have not voted
    users_data = [
        {"id": 1, "name": "User 1", "email": "user1@example.com", "role": "voter"},
        {"id": 2, "name": "User 2", "email": "user2@example.com", "role": "voter"},
    ]
    voters_data = [
        {"user_id": 1, "has_voted": False},
        {"user_id": 2, "has_voted": False},
    ]
    create_test_users_and_voters(users_data, voters_data)

    # Act: Call the endpoint
    response = client.get("voters/users/voting-status")

    # Assert: Verify the response
    assert response.status_code == 200
    assert response.json() == {
        "voted": [],
        "not_voted": [
            {"id": 1, "name": "User 1", "email": "user1@example.com"},
            {"id": 2, "name": "User 2", "email": "user2@example.com"}
        ]
    }

    test_db.rollback()
    gc.collect()

def test_voting_status_no_users(test_db, client):
    # Act: Call the endpoint when no users exist
    response = client.get("voters/users/voting-status")

    # Assert: Verify the response
    assert response.status_code == 200
    assert response.json() == {
        "voted": [],
        "not_voted": []
    }

    test_db.rollback()
    gc.collect()

def test_voter_details_success(test_db, create_test_voter, client):
    # Arrange: Create a voter with an associated user
    user_data = {"id": 1, "name": "John Doe", "email": "john.doe@example.com", "role": "voter"}
    voter_data = {"has_voted": True}
    user, voter = create_test_voter(user_data, voter_data)

    # # Act: Call the endpoint
    response = client.get(f"/voters/voter/{voter.id}")

    print(response.json())

    # # Assert: Verify the response
    assert response.status_code == 200
    assert response.json() == {
        "voter_id": voter.id,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
        "has_voted": voter.has_voted,
    }

    test_db.rollback()
    gc.collect()

def test_voter_details_not_found(test_db, client):
    # Act: Call the endpoint for a non-existent voter
    response = client.get("/voters/voter/999")

    # Assert: Verify the response
    assert response.status_code == 404
    assert response.json() == {"detail": "Voter with ID 999 not found."}

    test_db.rollback()
    gc.collect()

def test_inactive_voters_present(test_db, create_test_voters, client):
    # Arrange: Create users and voters
    users_data = [
        {"id": 1, "name": "John Doe", "email": "john.doe@example.com", "role": "voter"},
        {"id": 2, "name": "Jane Smith", "email": "jane.smith@example.com", "role": "voter"},
    ]
    voters_data = [
        {"user_id": 1, "has_voted": False},
        {"user_id": 2, "has_voted": False},
    ]
    create_test_voters(users_data, voters_data)

    # Act: Call the endpoint
    response = client.get("/voters/inactive/")

    # Assert: Verify the inactive voters
    assert response.status_code == 200
    assert response.json() == [
        {"voter_id": 1, "user_id": 1},
        {"voter_id": 2, "user_id": 2},
    ]

    test_db.rollback()
    gc.collect()

def test_no_voters_in_database(test_db, client):
    # Act: Call the endpoint when there are no voters
    response = client.get("/voters/inactive/")

    # Assert: Verify the response
    assert response.status_code == 200
    assert response.json() == []

    test_db.rollback()
    gc.collect()

def test_all_voters_active(test_db, create_test_voters, client):
    # Arrange: Create users and voters who have all voted
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
    ]
    create_test_voters(users_data, voters_data)

    # Act: Call the endpoint
    response = client.get("/voters/inactive/")

    # Assert: Verify the response
    assert response.status_code == 200
    assert response.json() == []

    test_db.rollback()
    gc.collect()

def test_bulk_voter_upload_success(test_db, get_voter_count, client):
    # Arrange: Define the voter upload request
    request_data = {
        "voters": [
            {"name": "Alice Johnson", "email": "alice@example.com", "role": "voter"},
            {"name": "Bob Smith", "email": "bob@example.com", "role": "admin"}
        ]
    }
    initial_voter_count = get_voter_count()

    # Act: Call the endpoint
    response = client.post("/voters/bulk-upload", json=request_data)

    # Assert: Verify bulk insertion success
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert get_voter_count() == initial_voter_count + 2  # Ensure voters were added

    test_db.rollback()
    gc.collect()