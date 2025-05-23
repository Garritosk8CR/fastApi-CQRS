from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from app.infrastructure.models import Candidate, Election, Observer, ObserverFeedback, User, Vote, Voter
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
def create_test_votes(test_db):
    def _create(vote_data):
        votes = []
        for data in vote_data:
            vote = Vote(**data)
            test_db.add(vote)
            votes.append(vote)
        test_db.commit()
        return votes
    return _create

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

@pytest.fixture
def create_test_candidates(test_db):
    def _create_candidates(candidates_data):
        candidates = []
        for candidate_data in candidates_data:
            candidate = Candidate(**candidate_data)
            test_db.add(candidate)
            candidates.append(candidate)
        test_db.commit()
        return candidates
    return _create_candidates

@pytest.fixture
def create_test_feedback(test_db):
    def _create(feedback_data):
        feedbacks = []
        for data in feedback_data:
            feedback = ObserverFeedback(**data)
            test_db.add(feedback)
            feedbacks.append(feedback)
        test_db.commit()
        return feedbacks
    return _create

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
    print(vote_response.json())
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

def test_bulk_voter_upload_empty_request(test_db, client):
    # Arrange: Define an empty voter list
    request_data = {"voters": []}

    # Act: Call the endpoint
    response = client.post("/voters/bulk-upload", json=request_data)

    # Assert: Verify response handling
    assert response.status_code == 200
    assert response.json() == []

    test_db.rollback()
    gc.collect()

def test_bulk_voter_upload_invalid_data(test_db, client):
    # Arrange: Define a request with invalid data format (missing required fields)
    request_data = {
        "voters": [
            {"name": "Charlie Brown"},  # Missing email and role
            {"email": "dana@example.com", "role": "admin"}  # Missing name
        ]
    }

    # Act: Call the endpoint
    response = client.post("/voters/bulk-upload", json=request_data)

    # Assert: Verify response validation
    assert response.status_code == 422  # Unprocessable entity due to validation errors

    test_db.rollback()
    gc.collect()

def test_election_summary_no_feedback(test_db, create_test_elections, create_test_votes, create_test_voters, create_test_candidates, client):
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"},
        {"id": 4, "name": "Active Voter 4", "email": "active4@example.com", "role": "voter"},
        {"id": 5, "name": "Active Voter 5", "email": "active5@example.com", "role": "voter"},
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True},
        {"user_id": 4, "has_voted": True},
        {"user_id": 5, "has_voted": True},
    ]
    candidates_data = [
        {"id": 1, "name": "Candidate A", "party": "Group X", "bio": "Experienced leader.", "election_id": 1},
        {"id": 2, "name": "Candidate B", "party": "Group Y", "bio": "Visionary thinker.", "election_id": 1},
        {"id": 3, "name": "Candidate C", "party": "Group Z", "bio": "Innovative innovator.", "election_id": 1},
        {"id": 4, "name": "Candidate D", "party": "Group X", "bio": "Experienced leader.", "election_id": 1},
        {"id": 5, "name": "Candidate E", "party": "Group Y", "bio": "Visionary thinker.", "election_id": 1},
        {"id": 6, "name": "Candidate F", "party": "Group Z", "bio": "Innovative innovator.", "election_id": 1},
    ]
    create_test_voters(users_data, voters_data)
    
    # Arrange: Create an election with ID 1
    create_test_elections([{"id": 1, "name": "Test Election"}])
    
    create_test_candidates(candidates_data)

    create_test_votes([
        {"id": 1, "election_id": 1, "voter_id": 1, "candidate_id": 1},
        {"id": 2, "election_id": 1, "voter_id": 2, "candidate_id": 2},
        {"id": 3, "election_id": 1, "voter_id": 3, "candidate_id": 3},
        {"id": 4, "election_id": 1, "voter_id": 4, "candidate_id": 4},
        {"id": 5, "election_id": 1, "voter_id": 5, "candidate_id": 5},
    ])
    # Act: Get the election summary for election_id=10
    response = client.get("/votes/analytics/election_summary?election_id=1")
    data = response.json()

    # Assert: Total votes should be 5; without feedback, sentiment & trust are None
    assert response.status_code == 200
    assert data["total_votes"] == 5
    assert data["average_sentiment"] is None
    assert data["average_observer_trust"] is None

    test_db.rollback()
    gc.collect()

def test_election_summary_with_feedback( test_db, create_test_elections, create_test_votes, create_test_feedback, create_test_voters, create_test_candidates, create_test_observers, client):
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"},
        {"id": 4, "name": "Active Voter 4", "email": "active4@example.com", "role": "voter"},
        {"id": 5, "name": "Active Voter 5", "email": "active5@example.com", "role": "voter"},
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True},
        {"user_id": 4, "has_voted": True},
        {"user_id": 5, "has_voted": True},
    ]
    candidates_data = [
        {"id": 1, "name": "Candidate A", "party": "Group X", "bio": "Experienced leader.", "election_id": 1},
        {"id": 2, "name": "Candidate B", "party": "Group Y", "bio": "Visionary thinker.", "election_id": 1},
        {"id": 3, "name": "Candidate C", "party": "Group Z", "bio": "Innovative innovator.", "election_id": 1},
        {"id": 4, "name": "Candidate D", "party": "Group X", "bio": "Experienced leader.", "election_id": 1},
        {"id": 5, "name": "Candidate E", "party": "Group Y", "bio": "Visionary thinker.", "election_id": 1},
        {"id": 6, "name": "Candidate F", "party": "Group Z", "bio": "Innovative innovator.", "election_id": 1},
    ]
    observers_data = [
        {"id": 1, "name": "Observer A", "email": "observerA@example.com", "election_id": 1, "organization": "Group X"},
        {"id": 2, "name": "Observer B", "email": "observerB@example.com", "election_id": 1, "organization": "Group Y"},
    ]
    
    # Arrange: Create an election with ID 1
    create_test_voters(users_data, voters_data)
    create_test_elections([{"id": 1, "name": "Election 1"}])
    create_test_candidates(candidates_data)
    create_test_votes([
        {"id": 1, "election_id": 1, "voter_id": 1, "candidate_id": 1},
        {"id": 2, "election_id": 1, "voter_id": 2, "candidate_id": 2},
        {"id": 3, "election_id": 1, "voter_id": 3, "candidate_id": 3},
    ])
    create_test_observers(observers_data)
    # ObserverFeedback records for election 1.
    # Observer 1 submits 2 reports, Observer 2 submits 1.
    create_test_feedback([
        {
            "id": 1, "observer_id": 1, "election_id": 1,
            "description": "Great process",  # Positive sentiment
            "severity": "LOW",
            "timestamp": datetime(2025, 5, 10, 10, 0, 0)
        },
        {
            "id": 2, "observer_id": 1, "election_id": 1,
            "description": "Smooth voting",  # Positive sentiment
            "severity": "LOW",
            "timestamp": datetime(2025, 5, 10, 11, 0, 0)
        },
        {
            "id": 3, "observer_id": 2, "election_id": 1,
            "description": "Issues observed",  # Likely a negative sentiment
            "severity": "HIGH",
            "timestamp": datetime(2025, 5, 10, 12, 0, 0)
        },
    ])
    
    # Act: Get the election summary for election_id=20
    response = client.get("/votes/analytics/election_summary?election_id=1")
    data = response.json()

    # Assert: Total votes should be 3.
    # For observer trust: Observer 1 made 2 reports (score = min(100, 2*10)=20) and Observer 2 made 1 (score=10).
    # Average trust = (20 + 10) / 2 = 15.
    assert response.status_code == 200
    assert data["total_votes"] == 3
    assert isinstance(data["average_sentiment"], float)
    assert data["average_observer_trust"] == 15

    test_db.rollback()
    gc.collect()


def test_sentiment_trend_with_feedback( client, test_db, create_test_elections, create_test_feedback, create_test_voters, create_test_candidates, create_test_observers ):

    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"},
        {"id": 4, "name": "Active Voter 4", "email": "active4@example.com", "role": "voter"},
        {"id": 5, "name": "Active Voter 5", "email": "active5@example.com", "role": "voter"},
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True},
        {"user_id": 4, "has_voted": True},
        {"user_id": 5, "has_voted": True},
    ]
    candidates_data = [
        {"id": 1, "name": "Candidate A", "party": "Group X", "bio": "Experienced leader.", "election_id": 1},
        {"id": 2, "name": "Candidate B", "party": "Group Y", "bio": "Visionary thinker.", "election_id": 1},
        {"id": 3, "name": "Candidate C", "party": "Group Z", "bio": "Innovative innovator.", "election_id": 1},
        {"id": 4, "name": "Candidate D", "party": "Group X", "bio": "Experienced leader.", "election_id": 1},
        {"id": 5, "name": "Candidate E", "party": "Group Y", "bio": "Visionary thinker.", "election_id": 1},
        {"id": 6, "name": "Candidate F", "party": "Group Z", "bio": "Innovative innovator.", "election_id": 1},
    ]
    observers_data = [
        {"id": 1, "name": "Observer A", "email": "observerA@example.com", "election_id": 1, "organization": "Group X"},
        {"id": 2, "name": "Observer B", "email": "observerB@example.com", "election_id": 1, "organization": "Group Y"},
    ]
    create_test_voters(users_data, voters_data)
    # Arrange: Create an election and feedback entries on different dates.
    create_test_elections([{"id": 1, "name": "Trend Election"}])
    create_test_candidates(candidates_data)
    create_test_observers(observers_data)
    create_test_feedback([
        {
            "id": 1,
            "observer_id": 1,
            "election_id": 1,
            "description": "Great process",         # Positive sentiment around 0.8
            "severity": "LOW",
            "timestamp": datetime(2025, 5, 10, 9, 0, 0)
        },
        {
            "id": 2,
            "observer_id": 2,
            "election_id": 1,
            "description": "Smooth voting",          # Positive sentiment
            "severity": "LOW",
            "timestamp": datetime(2025, 5, 10, 10, 0, 0)
        },
        {
            "id": 3,
            "observer_id": 1,
            "election_id": 1,
            "description": "Issues observed",        # Negative sentiment
            "severity": "HIGH",
            "timestamp": datetime(2025, 5, 11, 11, 0, 0)
        },
    ])
    
    # Act: Call the endpoint for election_id 1.
    response = client.get("/votes/analytics/sentiment_trend?election_id=1")
    data = response.json()
    
    # Assert: Verify we have entries for the two dates.
    assert response.status_code == 200
    # Expect two dates: one for 2025-05-10 and one for 2025-05-11.
    dates = [entry["date"] for entry in data]
    assert "2025-05-10" in dates
    assert "2025-05-11" in dates

    test_db.rollback()
    gc.collect()

def test_candidate_vote_distribution( test_db, create_test_elections, create_test_candidates, create_test_votes, create_test_voters, client):
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"},
        {"id": 4, "name": "Active Voter 4", "email": "active4@example.com", "role": "voter"},
        {"id": 5, "name": "Active Voter 5", "email": "active5@example.com", "role": "voter"},
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True},
        {"user_id": 4, "has_voted": True},
        {"user_id": 5, "has_voted": True},
    ]
    create_test_voters(users_data, voters_data)
    # Arrange: Create an election, candidates, and votes.
    create_test_elections([{"id": 1, "name": "Election 1"}])
    create_test_candidates([
         {"id": 1, "name": "Candidate A", "party": "Group X", "bio": "Experienced leader.", "election_id": 1},
        {"id": 2, "name": "Candidate B", "party": "Group Y", "bio": "Visionary thinker.", "election_id": 1},
        {"id": 3, "name": "Candidate C", "party": "Group Z", "bio": "Innovative innovator.", "election_id": 1}
    ])
    create_test_votes([
         {"id": 1, "election_id": 1, "candidate_id": 1, "voter_id": 1},
         {"id": 2, "election_id": 1, "candidate_id": 1, "voter_id": 2},
         {"id": 3, "election_id": 1, "candidate_id": 2, "voter_id": 3}
    ])
    
    # Act: Call the endpoint.
    response = client.get("/votes/analytics/candidate_distribution?election_id=1")
    
    # Assert: Verify candidate vote counts and percentages.
    data = response.json()
    assert response.status_code == 200
    candidate_a = next(item for item in data if item["candidate_id"] == 1)
    candidate_b = next(item for item in data if item["candidate_id"] == 2)
    assert candidate_a["vote_count"] == 2
    assert candidate_a["vote_percentage"] == 66.67
    assert candidate_b["vote_count"] == 1
    assert candidate_b["vote_percentage"] == 33.33

    test_db.rollback()
    gc.collect()

def test_voting_patterns_hourly( test_db, create_test_elections, create_test_votes, create_test_voters, create_test_candidates, client):
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"},
        {"id": 4, "name": "Active Voter 4", "email": "active4@example.com", "role": "voter"},
        {"id": 5, "name": "Active Voter 5", "email": "active5@example.com", "role": "voter"},
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True},
        {"user_id": 4, "has_voted": True},
        {"user_id": 5, "has_voted": True},
    ]
    create_test_voters(users_data, voters_data)
    # Arrange: Create an election and votes at different timestamps
    create_test_elections([{"id": 1, "name": "Election 1"}])
    create_test_candidates([
         {"id": 1, "name": "Candidate A", "party": "Group X", "bio": "Experienced leader.", "election_id": 1},
        {"id": 2, "name": "Candidate B", "party": "Group Y", "bio": "Visionary thinker.", "election_id": 1},
        {"id": 3, "name": "Candidate C", "party": "Group Z", "bio": "Innovative innovator.", "election_id": 1}
    ])
    create_test_votes([
        {"id": 1, "election_id": 1, "voter_id": 1, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 9, 15, 0)},
        {"id": 2, "election_id": 1, "voter_id": 2, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 9, 45, 0)},
        {"id": 3, "election_id": 1, "voter_id": 3, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 10, 5, 0)},
        {"id": 4, "election_id": 1, "voter_id": 4, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 11, 30, 0)}
    ])

    # Act: Request hourly voting trends
    response = client.get("/votes/analytics/voting_patterns?election_id=1&interval=hourly")
    
    # Assert: Verify correct hourly grouping
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 3  # Expecting trends for 9:00, 10:00, 11:00
    assert data[0]["time_period"].startswith("2025-05-10T09")
    assert data[1]["time_period"].startswith("2025-05-10T10")
    assert data[2]["time_period"].startswith("2025-05-10T11")

    test_db.rollback()
    gc.collect()

def test_voting_patterns_daily( test_db, create_test_elections, create_test_votes, create_test_voters, create_test_candidates, client):
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"},
        {"id": 4, "name": "Active Voter 4", "email": "active4@example.com", "role": "voter"},
        {"id": 5, "name": "Active Voter 5", "email": "active5@example.com", "role": "voter"},
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True},
        {"user_id": 4, "has_voted": True},
        {"user_id": 5, "has_voted": True},
    ]
    create_test_voters(users_data, voters_data)
    # Arrange: Create an election and votes spread across multiple days
    create_test_elections([{"id": 1, "name": "Election 1"}])
    create_test_candidates([
         {"id": 1, "name": "Candidate A", "party": "Group X", "bio": "Experienced leader.", "election_id": 1},
        {"id": 2, "name": "Candidate B", "party": "Group Y", "bio": "Visionary thinker.", "election_id": 1},
        {"id": 3, "name": "Candidate C", "party": "Group Z", "bio": "Innovative innovator.", "election_id": 1}
    ])
    create_test_votes([
        {"id": 1, "election_id": 1, "voter_id": 1, "candidate_id": 1, "timestamp": datetime(2025, 5, 8, 14, 0, 0)},
        {"id": 2, "election_id": 1, "voter_id": 2, "candidate_id": 1, "timestamp": datetime(2025, 5, 9, 10, 0, 0)},
        {"id": 3, "election_id": 1, "voter_id": 3, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 16, 0, 0)}
    ])

    # Act: Request daily voting trends
    response = client.get("/votes/analytics/voting_patterns?election_id=1&interval=daily")
    
    # Assert: Verify correct daily grouping
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 3  # Expecting entries for May 8, May 9, and May 10
    assert data[0]["time_period"].startswith("2025-05-08")
    assert data[1]["time_period"].startswith("2025-05-09")
    assert data[2]["time_period"].startswith("2025-05-10")

    test_db.rollback()
    gc.collect()

def test_historical_turnout_trends( test_db, create_test_elections, create_test_votes, create_test_voters, create_test_candidates, client):

    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"},
        {"id": 4, "name": "Active Voter 4", "email": "active4@example.com", "role": "voter"},
        {"id": 5, "name": "Active Voter 5", "email": "active5@example.com", "role": "voter"},
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True},
        {"user_id": 4, "has_voted": True},
        {"user_id": 5, "has_voted": True},
    ]
    create_test_voters(users_data, voters_data)
    # Arrange: Create elections and votes over multiple years
    create_test_elections([
        {"id": 1, "name": "Election 2021"},
        {"id": 2, "name": "Election 2022"},
        {"id": 3, "name": "Election 2023"}
    ])
    create_test_candidates([
         {"id": 1, "name": "Candidate A", "party": "Group X", "bio": "Experienced leader.", "election_id": 1},
        {"id": 2, "name": "Candidate B", "party": "Group Y", "bio": "Visionary thinker.", "election_id": 1},
        {"id": 3, "name": "Candidate C", "party": "Group Z", "bio": "Innovative innovator.", "election_id": 1}
    ])
    create_test_votes([
        {"id": 1, "election_id": 1, "voter_id": 1, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 9, 15, 0)},
        {"id": 2, "election_id": 1, "voter_id": 2, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 9, 45, 0)},
        {"id": 3, "election_id": 1, "voter_id": 3, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 10, 5, 0)},
        {"id": 4, "election_id": 1, "voter_id": 4, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 11, 30, 0)},
        {"id": 5, "election_id": 1, "voter_id": 5, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 12, 0, 0)},
        {"id": 6, "election_id": 2, "voter_id": 1, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 9, 15, 0)},
        {"id": 7, "election_id": 2, "voter_id": 2, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 9, 45, 0)},
        {"id": 8, "election_id": 2, "voter_id": 3, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 10, 5, 0)},
        {"id": 9, "election_id": 2, "voter_id": 4, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 11, 30, 0)},
        {"id": 10, "election_id": 2, "voter_id": 5, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 12, 0, 0)},
        {"id": 11, "election_id": 3, "voter_id": 1, "candidate_id": 1, "timestamp": datetime(2027, 5, 10, 9, 15, 0)},
        {"id": 12, "election_id": 3, "voter_id": 2, "candidate_id": 1, "timestamp": datetime(2027, 5, 10, 9, 45, 0)},
    ])

    # Act: Request historical turnout trends
    response = client.get("/votes/analytics/turnout_trends?election_ids=1,2,3")

    # Assert: Verify correct turnout calculations
    data = response.json()
    assert response.status_code == 200
    print(data)
    test_db.rollback()
    gc.collect()
    assert len(data) == 3
    
    assert data[0]["vote_count"] == 5  # Election 2021 turnout
    assert data[1]["vote_count"] == 5  # Election 2022 turnout
    assert data[2]["vote_count"] == 2  # Election 2023 turnout
    assert data[1]["percentage_change"] == 0.0  # Increase from 2 to 3 votes
    assert data[2]["percentage_change"] == -60.0  # Increase from 3 to 4 votes

def test_turnout_forecasting_with_historical_data(test_db, create_test_elections, create_test_votes, create_test_voters, create_test_candidates, client):
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"},
        {"id": 4, "name": "Active Voter 4", "email": "active4@example.com", "role": "voter"},
        {"id": 5, "name": "Active Voter 5", "email": "active5@example.com", "role": "voter"},
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True},
        {"user_id": 4, "has_voted": True},
        {"user_id": 5, "has_voted": True},
    ]
    create_test_voters(users_data, voters_data)
    # Arrange: Create elections and votes over multiple years
    create_test_elections([
        {"id": 1, "name": "Election 2021"},
        {"id": 2, "name": "Election 2022"},
        {"id": 3, "name": "Election 2023"},
        {"id": 4, "name": "Upcoming Election"}
    ])
    create_test_candidates([
         {"id": 1, "name": "Candidate A", "party": "Group X", "bio": "Experienced leader.", "election_id": 1},
        {"id": 2, "name": "Candidate B", "party": "Group Y", "bio": "Visionary thinker.", "election_id": 1},
        {"id": 3, "name": "Candidate C", "party": "Group Z", "bio": "Innovative innovator.", "election_id": 1}
    ])
    create_test_votes([
        {"id": 1, "election_id": 1, "voter_id": 1, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 9, 15, 0)},
        {"id": 2, "election_id": 1, "voter_id": 2, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 9, 45, 0)},
        {"id": 3, "election_id": 1, "voter_id": 3, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 10, 5, 0)},
        {"id": 4, "election_id": 1, "voter_id": 4, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 11, 30, 0)},
        {"id": 5, "election_id": 1, "voter_id": 5, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 12, 0, 0)},
        {"id": 6, "election_id": 2, "voter_id": 1, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 9, 15, 0)},
        {"id": 7, "election_id": 2, "voter_id": 2, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 9, 45, 0)},
        {"id": 8, "election_id": 2, "voter_id": 3, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 10, 5, 0)},
        {"id": 9, "election_id": 2, "voter_id": 4, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 11, 30, 0)},
    ])

    # Act: Request turnout forecast for election_id=4
    response = client.get("/votes/analytics/turnout_forecast?election_id=4&lookback=3")

    # Assert: Verify correct turnout predictions
    data = response.json()
    test_db.rollback()
    gc.collect()
    assert response.status_code == 200
    assert data["predicted_turnout"] == 4  # Moving average of last 3 elections


def test_seasonal_turnout_forecasting( test_db, create_test_elections, create_test_votes , create_test_voters, create_test_candidates, client):
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"},
        {"id": 4, "name": "Active Voter 4", "email": "active4@example.com", "role": "voter"},
        {"id": 5, "name": "Active Voter 5", "email": "active5@example.com", "role": "voter"},
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True},
        {"user_id": 4, "has_voted": True},
        {"user_id": 5, "has_voted": True},
    ]
    create_test_voters(users_data, voters_data)
    # Arrange: Create elections spread across different months
    create_test_elections([
        {"id": 1, "name": "Election 2021"},
        {"id": 2, "name": "Election 2022"},
        {"id": 3, "name": "Election 2023"},
        {"id": 4, "name": "Upcoming Election"}
    ])
    create_test_candidates([
         {"id": 1, "name": "Candidate A", "party": "Group X", "bio": "Experienced leader.", "election_id": 1},
        {"id": 2, "name": "Candidate B", "party": "Group Y", "bio": "Visionary thinker.", "election_id": 1},
        {"id": 3, "name": "Candidate C", "party": "Group Z", "bio": "Innovative innovator.", "election_id": 1}
    ])
    create_test_votes([
        {"id": 1, "election_id": 1, "voter_id": 1, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 9, 15, 0)},
        {"id": 2, "election_id": 1, "voter_id": 2, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 9, 45, 0)},
        {"id": 3, "election_id": 2, "voter_id": 3, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 10, 5, 0)},
        {"id": 4, "election_id": 2, "voter_id": 4, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 11, 30, 0)},
        {"id": 5, "election_id": 2, "voter_id": 5, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 12, 0, 0)},
        {"id": 6, "election_id": 3, "voter_id": 1, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 9, 15, 0)},
        {"id": 7, "election_id": 3, "voter_id": 2, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 9, 45, 0)},
        {"id": 8, "election_id": 3, "voter_id": 3, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 10, 5, 0)},
        {"id": 9, "election_id": 3, "voter_id": 4, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 11, 30, 0)},
    ])

    # Act: Request turnout forecast for election_id=4 (January election)
    response = client.get("/votes/analytics/turnout_forecast/seasonal?election_id=3&lookback=5&weight_factor=1.5")

    test_db.rollback()
    gc.collect()

    # Assert: Verify turnout predictions factor in seasonality
    data = response.json()
    print(data)
    assert response.status_code == 200
    assert data["predicted_turnout"] > 2  # Elections matching January should be weighted more

    