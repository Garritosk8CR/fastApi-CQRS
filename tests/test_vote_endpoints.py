from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from app.infrastructure.models import Candidate, Election, Observer, ObserverFeedback, PollingStation, User, Vote, Voter
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


def test_turnout_confidence_high(test_db, create_test_elections, create_test_votes , create_test_voters, create_test_candidates, client):
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
    # Arrange: Create elections with stable turnout numbers
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

    # Act: Request turnout confidence scoring
    response = client.get("/votes/analytics/turnout_forecast/confidence?election_id=3&lookback=3")

    test_db.rollback()
    gc.collect()
    

    # Assert: Verify confidence is high due to low variability
    data = response.json()
    assert response.status_code == 200
    assert data["confidence_score"] == "High Confidence 🔵"

def test_turnout_confidence_low(test_db, create_test_elections, create_test_votes, create_test_voters, create_test_candidates, client):
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"},
        {"id": 4, "name": "Active Voter 4", "email": "active4@example.com", "role": "voter"},
        {"id": 5, "name": "Active Voter 5", "email": "active5@example.com", "role": "voter"},
        {"id": 6, "name": "Active Voter 6", "email": "active6@example.com", "role": "voter"},
        {"id": 7, "name": "Active Voter 7", "email": "active7@example.com", "role": "voter"},
        {"id": 8, "name": "Active Voter 8", "email": "active8@example.com", "role": "voter"},
        {"id": 9, "name": "Active Voter 9", "email": "active9@example.com", "role": "voter"},
        {"id": 10, "name": "Active Voter 10", "email": "active10@example.com", "role": "voter"},
        {"id": 11, "name": "Active Voter 11", "email": "active11@example.com", "role": "voter"},
        {"id": 12, "name": "Active Voter 12", "email": "active12@example.com", "role": "voter"},
        {"id": 13, "name": "Active Voter 13", "email": "active13@example.com", "role": "voter"},
        {"id": 14, "name": "Active Voter 14", "email": "active14@example.com", "role": "voter"},
        {"id": 15, "name": "Active Voter 15", "email": "active15@example.com", "role": "voter"},
        {"id": 16, "name": "Active Voter 16", "email": "active16@example.com", "role": "voter"},
        {"id": 17, "name": "Active Voter 17", "email": "active17@example.com", "role": "voter"},
        {"id": 18, "name": "Active Voter 18", "email": "active18@example.com", "role": "voter"},
        {"id": 19, "name": "Active Voter 19", "email": "active19@example.com", "role": "voter"},
        {"id": 20, "name": "Active Voter 20", "email": "active20@example.com", "role": "voter"},
        {"id": 21, "name": "Active Voter 21", "email": "active21@example.com", "role": "voter"},
        {"id": 22, "name": "Active Voter 22", "email": "active22@example.com", "role": "voter"},
        {"id": 23, "name": "Active Voter 23", "email": "active23@example.com", "role": "voter"},
        {"id": 24, "name": "Active Voter 24", "email": "active24@example.com", "role": "voter"},
        {"id": 25, "name": "Active Voter 25", "email": "active25@example.com", "role": "voter"},
        {"id": 26, "name": "Active Voter 26", "email": "active26@example.com", "role": "voter"},
        {"id": 27, "name": "Active Voter 27", "email": "active27@example.com", "role": "voter"},
        {"id": 28, "name": "Active Voter 28", "email": "active28@example.com", "role": "voter"},
        {"id": 29, "name": "Active Voter 29", "email": "active29@example.com", "role": "voter"},
        {"id": 30, "name": "Active Voter 30", "email": "active30@example.com", "role": "voter"},
        {"id": 31, "name": "Active Voter 31", "email": "active31@example.com", "role": "voter"},
        {"id": 32, "name": "Active Voter 32", "email": "active32@example.com", "role": "voter"},
        {"id": 33, "name": "Active Voter 33", "email": "active33@example.com", "role": "voter"},
        {"id": 34, "name": "Active Voter 34", "email": "active34@example.com", "role": "voter"},
        {"id": 35, "name": "Active Voter 35", "email": "active35@example.com", "role": "voter"},
        {"id": 36, "name": "Active Voter 36", "email": "active36@example.com", "role": "voter"},
        {"id": 37, "name": "Active Voter 37", "email": "active37@example.com", "role": "voter"},
        {"id": 38, "name": "Active Voter 38", "email": "active38@example.com", "role": "voter"},
        {"id": 39, "name": "Active Voter 39", "email": "active39@example.com", "role": "voter"},
        {"id": 40, "name": "Active Voter 40", "email": "active40@example.com", "role": "voter"},
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True},
        {"user_id": 4, "has_voted": True},
        {"user_id": 5, "has_voted": True},
        {"user_id": 6, "has_voted": True},
        {"user_id": 7, "has_voted": True},
        {"user_id": 8, "has_voted": True},
        {"user_id": 9, "has_voted": True},
        {"user_id": 10, "has_voted": True},
        {"user_id": 11, "has_voted": True},
        {"user_id": 12, "has_voted": True},
        {"user_id": 13, "has_voted": True},
        {"user_id": 14, "has_voted": True},
        {"user_id": 15, "has_voted": True},
        {"user_id": 16, "has_voted": True},
        {"user_id": 17, "has_voted": True},
        {"user_id": 18, "has_voted": True},
        {"user_id": 19, "has_voted": True},
        {"user_id": 20, "has_voted": True},
        {"user_id": 21, "has_voted": True},
        {"user_id": 22, "has_voted": True},
        {"user_id": 23, "has_voted": True},
        {"user_id": 24, "has_voted": True},
        {"user_id": 25, "has_voted": True},
        {"user_id": 26, "has_voted": True},
        {"user_id": 27, "has_voted": True},
        {"user_id": 28, "has_voted": True},
        {"user_id": 29, "has_voted": True},
        {"user_id": 30, "has_voted": True},
        {"user_id": 31, "has_voted": True},
        {"user_id": 32, "has_voted": True},
        {"user_id": 33, "has_voted": True},
        {"user_id": 34, "has_voted": True},
        {"user_id": 35, "has_voted": True},
        {"user_id": 36, "has_voted": True},
        {"user_id": 37, "has_voted": True},
        {"user_id": 38, "has_voted": True},
        {"user_id": 39, "has_voted": True},
        {"user_id": 40, "has_voted": True},
    ]
    create_test_voters(users_data, voters_data)
    # Arrange: Create elections with inconsistent turnout numbers
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
        # Low turnout in first election (very few voters)
        {"id": 1, "election_id": 1, "voter_id": 1, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 9, 15, 0)},
        {"id": 2, "election_id": 1, "voter_id": 2, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 9, 45, 0)},

        # Gradual increase in second election
        {"id": 3, "election_id": 2, "voter_id": 3, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 10, 5, 0)},
        {"id": 4, "election_id": 2, "voter_id": 4, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 11, 30, 0)},
        {"id": 5, "election_id": 2, "voter_id": 5, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 12, 0, 0)},

        # Huge surge in third election (Anomaly detected!)
        {"id": 6, "election_id": 3, "voter_id": 6, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 9, 15, 0)},
        {"id": 7, "election_id": 3, "voter_id": 7, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 9, 45, 0)},
        {"id": 8, "election_id": 3, "voter_id": 8, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 10, 5, 0)},
        {"id": 9, "election_id": 3, "voter_id": 9, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 11, 30, 0)},
        {"id": 10, "election_id": 3, "voter_id": 10, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 12, 0, 0)},
        {"id": 11, "election_id": 3, "voter_id": 11, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 12, 10, 0)},
        {"id": 12, "election_id": 3, "voter_id": 12, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 12, 20, 0)},
        {"id": 13, "election_id": 3, "voter_id": 13, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 12, 30, 0)},
        {"id": 14, "election_id": 3, "voter_id": 14, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 12, 40, 0)},
        {"id": 15, "election_id": 3, "voter_id": 15, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 12, 50, 0)},
        {"id": 16, "election_id": 3, "voter_id": 16, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 13, 0, 0)},
        {"id": 17, "election_id": 3, "voter_id": 17, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 13, 10, 0)},
        {"id": 18, "election_id": 3, "voter_id": 18, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 13, 20, 0)},
        {"id": 19, "election_id": 3, "voter_id": 19, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 13, 30, 0)},
        {"id": 20, "election_id": 3, "voter_id": 20, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 13, 40, 0)},
        {"id": 21, "election_id": 3, "voter_id": 21, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 13, 50, 0)},
        {"id": 22, "election_id": 3, "voter_id": 22, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 14, 0, 0)},
        {"id": 23, "election_id": 3, "voter_id": 23, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 14, 10, 0)},
        {"id": 24, "election_id": 3, "voter_id": 24, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 14, 20, 0)},
        {"id": 25, "election_id": 3, "voter_id": 25, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 14, 30, 0)},
        {"id": 26, "election_id": 3, "voter_id": 26, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 14, 40, 0)},
        {"id": 27, "election_id": 3, "voter_id": 27, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 14, 50, 0)},
        {"id": 28, "election_id": 3, "voter_id": 28, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 15, 0, 0)},
        {"id": 29, "election_id": 3, "voter_id": 29, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 15, 10, 0)},
        {"id": 30, "election_id": 3, "voter_id": 30, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 15, 20, 0)},
        {"id": 31, "election_id": 3, "voter_id": 31, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 15, 30, 0)},
        {"id": 32, "election_id": 3, "voter_id": 32, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 15, 40, 0)},
        {"id": 33, "election_id": 3, "voter_id": 33, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 15, 50, 0)},
        {"id": 34, "election_id": 3, "voter_id": 34, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 16, 0, 0)},
        {"id": 35, "election_id": 3, "voter_id": 35, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 16, 10, 0)},
        {"id": 36, "election_id": 3, "voter_id": 36, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 16, 20, 0)},
        {"id": 37, "election_id": 3, "voter_id": 37, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 16, 30, 0)},
        {"id": 38, "election_id": 3, "voter_id": 38, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 16, 40, 0)},
        {"id": 39, "election_id": 3, "voter_id": 39, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 16, 50, 0)},
        {"id": 40, "election_id": 3, "voter_id": 40, "candidate_id": 1, "timestamp": datetime(2026, 5, 10, 17, 0, 0)}
    ])

    # Act: Request turnout confidence scoring
    response = client.get("/votes/analytics/turnout_forecast/confidence?election_id=38&lookback=10")

    test_db.rollback()
    gc.collect()
    # Assert: Verify confidence is low due to inconsistent turnout history
    data = response.json()
    assert response.status_code == 200
    assert data["confidence_score"] == "Low Confidence 🔴"

def test_detailed_historical_comparisons(test_db, create_test_elections, create_test_votes, create_test_voters, create_test_candidates, client):
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"},
        {"id": 4, "name": "Active Voter 4", "email": "active4@example.com", "role": "voter"},
        {"id": 5, "name": "Active Voter 5", "email": "active5@example.com", "role": "voter"},
        {"id": 6, "name": "Active Voter 6", "email": "active6@example.com", "role": "voter"},
        {"id": 7, "name": "Active Voter 7", "email": "active7@example.com", "role": "voter"},
        {"id": 8, "name": "Active Voter 8", "email": "active8@example.com", "role": "voter"},
        {"id": 9, "name": "Active Voter 9", "email": "active9@example.com", "role": "voter"},
        {"id": 10, "name": "Active Voter 10", "email": "active10@example.com", "role": "voter"},
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True},
        {"user_id": 4, "has_voted": True},
        {"user_id": 5, "has_voted": True},
        {"user_id": 6, "has_voted": True},
        {"user_id": 7, "has_voted": True},
        {"user_id": 8, "has_voted": True},
        {"user_id": 9, "has_voted": True},
        {"user_id": 10, "has_voted": True},
    ]
    create_test_voters(users_data, voters_data)
    # Arrange: Create elections with their associated votes (with timestamps)
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
        # Election 1 (Baseline: 2 votes, earliest timestamp)
        {"id": 1, "election_id": 1, "voter_id": 1, "candidate_id": 1, "timestamp": datetime(2021, 5, 10, 10, 0, 0)},
        {"id": 2, "election_id": 1, "voter_id": 2, "candidate_id": 1, "timestamp": datetime(2021, 5, 10, 11, 0, 0)},

        # Election 2 (4 votes → Expect a significant increase from 2 votes)
        {"id": 3, "election_id": 2, "voter_id": 3, "candidate_id": 1, "timestamp": datetime(2022, 5, 10, 9, 0, 0)},
        {"id": 4, "election_id": 2, "voter_id": 4, "candidate_id": 1, "timestamp": datetime(2022, 5, 10, 9, 15, 0)},
        {"id": 5, "election_id": 2, "voter_id": 5, "candidate_id": 1, "timestamp": datetime(2022, 5, 10, 10, 0, 0)},
        {"id": 6, "election_id": 2, "voter_id": 6, "candidate_id": 1, "timestamp": datetime(2022, 5, 10, 10, 30, 0)},

        # Election 3 (3 votes → Drop from 4 votes)
        {"id": 7, "election_id": 3, "voter_id": 7, "candidate_id": 1, "timestamp": datetime(2023, 5, 10, 9, 0, 0)},
        {"id": 8, "election_id": 3, "voter_id": 8, "candidate_id": 1, "timestamp": datetime(2023, 5, 10, 9, 15, 0)},
        {"id": 9, "election_id": 3, "voter_id": 9, "candidate_id": 1, "timestamp": datetime(2023, 5, 10, 9, 30, 0)}
    ])

    # Act: Request detailed historical comparisons for elections 1, 2, and 3
    response = client.get("/votes/analytics/historical_detailed?election_ids=1,2,3")

    test_db.rollback()
    gc.collect()

    data = response.json()

    # Assert: Check that annotations and metrics are computed correctly
    assert response.status_code == 200
    # First record should be baseline data (no previous election to compare)
    assert data[0]["annotation"] == "Baseline data"
    # Election 2: from 2 votes to 4 votes is a 100% increase → "Major Surge"
    assert data[1]["annotation"] == "Major Surge"
    # Election 3: from 4 votes to 3 votes → moderate drop; if -25% (which is > -30%), annotation should be "Stable turnout"
    assert data[2]["annotation"] == "Stable turnout"

def test_detailed_historical_comparisons_with_external(client, test_db, create_test_elections, create_test_votes , create_test_candidates, create_test_voters):
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"},
        {"id": 4, "name": "Active Voter 4", "email": "active4@example.com", "role": "voter"},
        {"id": 5, "name": "Active Voter 5", "email": "active5@example.com", "role": "voter"},
        {"id": 6, "name": "Active Voter 6", "email": "active6@example.com", "role": "voter"},
        {"id": 7, "name": "Active Voter 7", "email": "active7@example.com", "role": "voter"},
        {"id": 8, "name": "Active Voter 8", "email": "active8@example.com", "role": "voter"},
        {"id": 9, "name": "Active Voter 9", "email": "active9@example.com", "role": "voter"},
        {"id": 10, "name": "Active Voter 10", "email": "active10@example.com", "role": "voter"},
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True},
        {"user_id": 4, "has_voted": True},
        {"user_id": 5, "has_voted": True},
        {"user_id": 6, "has_voted": True},
        {"user_id": 7, "has_voted": True},
        {"user_id": 8, "has_voted": True},
        {"user_id": 9, "has_voted": True},
        {"user_id": 10, "has_voted": True},
    ]
    create_test_voters(users_data, voters_data)
    # Arrange: Create a few elections and their votes.
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
        # Election 1
        {"id": 1, "election_id": 1, "voter_id": 1, "candidate_id": 1, "timestamp": datetime(2021, 5, 10, 10, 0, 0)},
        {"id": 2, "election_id": 1, "voter_id": 2, "candidate_id": 1, "timestamp": datetime(2021, 5, 10, 11, 0, 0)},
        # Election 2
        {"id": 3, "election_id": 2, "voter_id": 3, "candidate_id": 1, "timestamp": datetime(2022, 5, 10, 9, 0, 0)},
        {"id": 4, "election_id": 2, "voter_id": 4, "candidate_id": 1, "timestamp": datetime(2022, 5, 10, 9, 15, 0)},
        {"id": 5, "election_id": 2, "voter_id": 5, "candidate_id": 1, "timestamp": datetime(2022, 5, 10, 10, 0, 0)},
        {"id": 6, "election_id": 2, "voter_id": 6, "candidate_id": 1, "timestamp": datetime(2022, 5, 10, 10, 30, 0)},
        # Election 3
        {"id": 7, "election_id": 3, "voter_id": 7, "candidate_id": 1, "timestamp": datetime(2023, 5, 10, 9, 0, 0)},
        {"id": 8, "election_id": 3, "voter_id": 8, "candidate_id": 1, "timestamp": datetime(2023, 5, 10, 9, 15, 0)},
        {"id": 9, "election_id": 3, "voter_id": 9, "candidate_id": 1, "timestamp": datetime(2023, 5, 10, 9, 30, 0)}
    ])

    # Act: Request enriched historical comparisons.
    response = client.get("/votes/analytics/historical_detailed/external?election_ids=1,2,3")

    test_db.rollback()
    gc.collect()

    data = response.json()

    # Assert: Verify that external data is added into each record.
    assert response.status_code == 200
    for record in data:
        assert "external" in record
        # Since we simulate weather based on election_id parity:
        expected_weather = "Sunny" if record["election_id"] % 2 == 0 else "Cloudy"
        assert record["external"]["weather"] == expected_weather

def test_dashboard_endpoint(test_db, create_test_elections, create_test_votes, create_test_voters, create_test_candidates, client):
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"},
        {"id": 4, "name": "Active Voter 4", "email": "active4@example.com", "role": "voter"},
        {"id": 5, "name": "Active Voter 5", "email": "active5@example.com", "role": "voter"},
        {"id": 6, "name": "Active Voter 6", "email": "active6@example.com", "role": "voter"},
        {"id": 7, "name": "Active Voter 7", "email": "active7@example.com", "role": "voter"},
        {"id": 8, "name": "Active Voter 8", "email": "active8@example.com", "role": "voter"},
        {"id": 9, "name": "Active Voter 9", "email": "active9@example.com", "role": "voter"},
        {"id": 10, "name": "Active Voter 10", "email": "active10@example.com", "role": "voter"},
        {"id": 11, "name": "Active Voter 11", "email": "active11@example.com", "role": "voter"},
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True},
        {"user_id": 4, "has_voted": True},
        {"user_id": 5, "has_voted": True},
        {"user_id": 6, "has_voted": True},
        {"user_id": 7, "has_voted": True},
        {"user_id": 8, "has_voted": True},
        {"user_id": 9, "has_voted": True},
        {"user_id": 10, "has_voted": True},
        {"user_id": 11, "has_voted": True},
    ]
    create_test_voters(users_data, voters_data)
    # Arrange: Create a few elections and their votes.
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
        # Election 1 (2 votes)
        {"id": 1, "election_id": 1, "voter_id": 1, "candidate_id": 1, "timestamp": datetime(2021, 5, 10, 10, 0, 0)},
        {"id": 2, "election_id": 1, "voter_id": 2, "candidate_id": 1, "timestamp": datetime(2021, 5, 10, 11, 0, 0)},
        
        # Election 2 (4 votes, candidate 1 gets 3 out of 4)
        {"id": 3, "election_id": 2, "voter_id": 3, "candidate_id": 1, "timestamp": datetime(2022, 5, 10, 9, 0, 0)},
        {"id": 4, "election_id": 2, "voter_id": 4, "candidate_id": 1, "timestamp": datetime(2022, 5, 10, 9, 15, 0)},
        {"id": 5, "election_id": 2, "voter_id": 5, "candidate_id": 1, "timestamp": datetime(2022, 5, 10, 10, 0, 0)},
        {"id": 6, "election_id": 2, "voter_id": 6, "candidate_id": 2, "timestamp": datetime(2022, 5, 10, 10, 30, 0)},

        # Election3 (Current election, 5 votes)
        {"id": 7, "election_id": 3, "voter_id": 7, "candidate_id": 1, "timestamp": datetime(2023, 5, 10, 9, 0, 0)},
        {"id": 8, "election_id": 3, "voter_id": 8, "candidate_id": 1, "timestamp": datetime(2023, 5, 10, 9, 15, 0)},
        {"id": 9, "election_id": 3, "voter_id": 9, "candidate_id": 2, "timestamp": datetime(2023, 5, 10, 9, 30, 0)},
        {"id": 10, "election_id": 3, "voter_id": 10, "candidate_id": 1, "timestamp": datetime(2023, 5, 10, 10, 0, 0)},
        {"id": 11, "election_id": 3, "voter_id": 11, "candidate_id": 2, "timestamp": datetime(2023, 5, 10, 10, 15, 0)},
    ])

    # Act: Request the dashboard for election 3.
    response = client.get("/votes/analytics/dashboard?election_id=3")

    test_db.rollback()
    gc.collect()

    data = response.json()

    # Assert: Verify the structure and values in the dashboard response.
    assert response.status_code == 200
    assert data["election_id"] == 3
    assert "total_votes" in data
    assert "candidate_distribution" in data
    assert "observer_sentiment" in data
    assert "historical_trend" in data
    assert "external_data" in data
    # Check mocked external data based on election_id (3 is odd, expect "Cloudy")
    assert data["external_data"]["weather"] == "Cloudy"

def test_real_time_summary_endpoint(test_db, create_test_elections, create_test_votes, create_test_voters, create_test_candidates, client):
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"}       
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True}
    ]
    create_test_voters(users_data, voters_data)
    # Arrange: Create an election and some votes.
    create_test_elections([
        {"id": 1, "name": "Real-Time Election Test"},
    ])
    create_test_candidates([
         {"id": 1, "name": "Candidate A", "party": "Group X", "bio": "Experienced leader.", "election_id": 1},
        {"id": 2, "name": "Candidate B", "party": "Group Y", "bio": "Visionary thinker.", "election_id": 1},
        {"id": 3, "name": "Candidate C", "party": "Group Z", "bio": "Innovative innovator.", "election_id": 1}
    ])
    create_test_votes([
        {"id": 1, "election_id": 1, "voter_id": 1, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 10, 0, 0)},
        {"id": 2, "election_id": 1, "voter_id": 2, "candidate_id": 2, "timestamp": datetime(2025, 5, 10, 10, 5, 0)},
        {"id": 3, "election_id": 1, "voter_id": 3, "candidate_id": 1, "timestamp": datetime(2025, 5, 10, 10, 10, 0)},
    ])

    # Act
    response = client.get("/votes/analytics/real_time_summary?election_id=1")

    test_db.rollback()
    gc.collect()

    data = response.json()

    # Assert
    assert response.status_code == 200
    assert data["election_id"] == 1
    assert data["total_votes"] == 3
    assert isinstance(data["candidate_distribution"], list)
    assert data["last_update"] is not None

def test_geolocation_analytics_endpoint(test_db, create_test_elections, create_test_votes, create_test_voters, create_test_candidates, client):
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"},
        {"id": 4, "name": "Active Voter 4", "email": "active4@example.com", "role": "voter"},
        {"id": 5, "name": "Active Voter 5", "email": "active5@example.com", "role": "voter"}
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True},
        {"user_id": 4, "has_voted": False},
        {"user_id": 5, "has_voted": False}
    ]
    create_test_voters(users_data, voters_data)
    # Arrange: Create an election and votes with a "region" field.
    create_test_elections([
        {"id": 1, "name": "Regional Election"}
    ])
    create_test_candidates([
         {"id": 1, "name": "Candidate A", "party": "Group X", "bio": "Experienced leader.", "election_id": 1},
        {"id": 2, "name": "Candidate B", "party": "Group Y", "bio": "Visionary thinker.", "election_id": 1},
        {"id": 3, "name": "Candidate C", "party": "Group Z", "bio": "Innovative innovator.", "election_id": 1}
    ])
    create_test_votes([
        {"id": 1, "election_id": 1, "voter_id": 1, "candidate_id": 1, "region": "North", "timestamp": datetime(2025, 5, 10, 10, 0, 0)},
        {"id": 2, "election_id": 1, "voter_id": 2, "candidate_id": 2, "region": "North", "timestamp": datetime(2025, 5, 10, 10, 5, 0)},
        {"id": 3, "election_id": 1, "voter_id": 3, "candidate_id": 1, "region": "South", "timestamp": datetime(2025, 5, 10, 10, 10, 0)},
        {"id": 4, "election_id": 1, "voter_id": 4, "candidate_id": 2, "region": "South", "timestamp": datetime(2025, 5, 10, 10, 15, 0)},
        {"id": 5, "election_id": 1, "voter_id": 5, "candidate_id": 1, "region": "North", "timestamp": datetime(2025, 5, 10, 10, 20, 0)},
    ])

    # Act: Request geolocation analytics for election 1.
    response = client.get("/votes/analytics/geolocation?election_id=1")

    test_db.rollback()
    gc.collect()

    data = response.json()

    # Assert: Verify the structure and content.
    assert response.status_code == 200
    assert isinstance(data, list)
    # Verify that for each region, we get total_votes and candidate distribution.
    regions = {entry["region"] for entry in data}
    assert "North" in regions
    assert "South" in regions

    # Optionally, check that candidate distribution is structured as expected.
    for region_data in data:
        assert "total_votes" in region_data
        assert "candidate_distribution" in region_data

def test_polling_station_analytics_endpoint(test_db, create_test_elections, create_test_votes, create_test_voters, create_test_candidates, create_test_polling_stations, client):
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"},
        {"id": 4, "name": "Active Voter 4", "email": "active4@example.com", "role": "voter"},
        {"id": 5, "name": "Active Voter 5", "email": "active5@example.com", "role": "voter"}
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True},
        {"user_id": 4, "has_voted": False},
        {"user_id": 5, "has_voted": False}
    ]
    create_test_voters(users_data, voters_data)
    # Arrange: Create an election and votes with a polling_station field.
    create_test_elections([
        {"id": 1, "name": "Station Analytics Election"}
    ])
    create_test_candidates([
        {"id": 1, "name": "Candidate A", "party": "Group X", "bio": "Experienced leader.", "election_id": 1},
        {"id": 2, "name": "Candidate B", "party": "Group Y", "bio": "Visionary thinker.", "election_id": 1},
        {"id": 3, "name": "Candidate C", "party": "Group Z", "bio": "Innovative innovator.", "election_id": 1}
    ])
    stations_data = [
        {"id": 1, "name": "Station A", "location": "School", "election_id": 1, "capacity": 300},
        {"id": 2, "name": "Station B", "location": "Park", "election_id": 1, "capacity": 200}
    ]
    create_test_polling_stations(stations_data)
    # Create votes with different timestamps for two polling stations.
    now = datetime.now(timezone.utc)
    create_test_votes([
        {"id": 1, "election_id": 1, "voter_id": 1, "candidate_id": 1, "polling_station_id": 1, "timestamp": now},
        {"id": 2, "election_id": 1, "voter_id": 2, "candidate_id": 1, "polling_station_id": 1, "timestamp": now + timedelta(seconds=60)},
        {"id": 3, "election_id": 1, "voter_id": 3, "candidate_id": 2, "polling_station_id": 1, "timestamp": now + timedelta(seconds=120)},
        {"id": 4, "election_id": 1, "voter_id": 4, "candidate_id": 1, "polling_station_id": 2, "timestamp": now + timedelta(seconds=30)},
        {"id": 5, "election_id": 1, "voter_id": 5, "candidate_id": 2, "polling_station_id": 2, "timestamp": now + timedelta(seconds=90)},
    ])

    # Act: Request polling station analytics for election with ID 1.
    response = client.get("/votes/analytics/polling_station?election_id=1")

    test_db.rollback()
    gc.collect()

    data = response.json()

    # Assert: Verify the structure and content.
    assert response.status_code == 200
    assert isinstance(data, list)
    print(data)
    # Check that we have insights for both Station A and Station B.
    stations = {entry["polling_station"]["name"] for entry in data}
    assert "Station A" in stations
    assert "Station B" in stations

    # Optionally, verify the average interval for Station A.
    for entry in data:
        if entry["polling_station"] == "Station A":
            # The intervals are 60 seconds between votes, so the average should be 60.
            assert abs(entry["average_interval_seconds"] - 60) < 1  # Allow small floating point differences.

def test_historical_polling_station_trends_endpoint(
    test_db, create_test_elections, create_test_polling_stations, create_test_votes, create_test_voters, create_test_candidates, client
):
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"},
        {"id": 4, "name": "Active Voter 4", "email": "active4@example.com", "role": "voter"},
        {"id": 5, "name": "Active Voter 5", "email": "active5@example.com", "role": "voter"}
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True},
        {"user_id": 4, "has_voted": False},
        {"user_id": 5, "has_voted": False}
    ]
    create_test_voters(users_data, voters_data)
    # Arrange: Create elections, polling stations, and votes across different elections.
    create_test_elections([
        {"id": 1, "name": "Election 2020"},
        {"id": 2, "name": "Election 2021"},
    ])
    create_test_candidates([
        {"id": 1, "name": "Candidate A", "party": "Group X", "bio": "Experienced leader.", "election_id": 1},
        {"id": 2, "name": "Candidate B", "party": "Group Y", "bio": "Visionary thinker.", "election_id": 1},
        {"id": 3, "name": "Candidate C", "party": "Group Z", "bio": "Innovative innovator.", "election_id": 1}
    ])
    stations = create_test_polling_stations([
        {"id": 1, "name": "Station A", "location": "School", "election_id": 1, "capacity": 300},
        {"id": 2, "name": "Station B", "location": "Park", "election_id": 1, "capacity": 200},
    ])

    now = datetime.now(timezone.utc)
    # Votes for Election 2020, Station A
    create_test_votes([
        {"id": 1, "election_id": 1, "voter_id": 1, "candidate_id": 1, "polling_station_id": 1, "timestamp": now},
        {"id": 2, "election_id": 1, "voter_id": 2, "candidate_id": 1, "polling_station_id": 1, "timestamp": now + timedelta(seconds=60)},
    ])
    # Votes for Election 2021, Station A
    create_test_votes([
        {"id": 3, "election_id": 2, "voter_id": 3, "candidate_id": 1, "polling_station_id": 1, "timestamp": now + timedelta(days=365)},
        {"id": 4, "election_id": 2, "voter_id": 4, "candidate_id": 1, "polling_station_id": 1, "timestamp": now + timedelta(days=365, seconds=90)},
    ])

    # Act: Request historical trends for elections 1 and 2.
    response = client.get("/votes/analytics/historical_polling_station_trends?election_ids=1,2&polling_station_id=1")

    test_db.rollback()
    gc.collect()

    data = response.json()

    # Assert: Verify the structure and content of the response.
    assert response.status_code == 200
    assert isinstance(data, list)
    for entry in data:
        assert "election_id" in entry
        assert "polling_station" in entry
        assert "total_votes" in entry
        assert "average_interval_seconds" in entry
        assert "peak_hour" in entry
        assert "votes_in_peak_hour" in entry

def test_historical_trends_no_votes(test_db, client, create_test_elections, create_test_polling_stations):
    # Arrange: Create an election and a polling station but no votes.
    create_test_elections([
        {"id": 1, "name": "Election 2020"},
    ])
    create_test_polling_stations([
        {"id": 1, "name": "Station A", "location": "School", "election_id": 1, "capacity": 300},
    ])

    response = client.get("/votes/analytics/historical_polling_station_trends?election_ids=1&polling_station_id=1")

    test_db.rollback()
    gc.collect()

    data = response.json()

    # Assert: When there are no votes, expect an empty list.
    assert response.status_code == 200
    assert data == []

def test_historical_trends_single_vote(test_db, client, create_test_elections, create_test_polling_stations, create_test_votes, create_test_voters, create_test_candidates):
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"},
        {"id": 4, "name": "Active Voter 4", "email": "active4@example.com", "role": "voter"},
        {"id": 5, "name": "Active Voter 5", "email": "active5@example.com", "role": "voter"}
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True},
        {"user_id": 4, "has_voted": False},
        {"user_id": 5, "has_voted": False}
    ]
    create_test_voters(users_data, voters_data)
    # Arrange: Create an election, polling station, and a single vote.
    create_test_elections([
        {"id": 1, "name": "Election 2020"},
    ])
    create_test_candidates([
        {"id": 1, "name": "Candidate A", "party": "Group X", "bio": "Experienced leader.", "election_id": 1},
        {"id": 2, "name": "Candidate B", "party": "Group Y", "bio": "Visionary thinker.", "election_id": 1},
        {"id": 3, "name": "Candidate C", "party": "Group Z", "bio": "Innovative innovator.", "election_id": 1}
    ])
    create_test_polling_stations([
        {"id": 1, "name": "Station A", "location": "School", "election_id": 1, "capacity": 300},
    ])
    now = datetime.now(timezone.utc)
    create_test_votes([
        {"id": 1, "election_id": 1, "voter_id": 1, "candidate_id": 1, "polling_station_id": 1, "timestamp": now},
    ])

    # Act: Call the endpoint.
    response = client.get("/votes/analytics/historical_polling_station_trends?election_ids=1&polling_station_id=1")

    test_db.rollback()
    gc.collect()

    data = response.json()

    # Assert: With one vote, total_votes is 1, and average_interval_seconds is None.
    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["total_votes"] == 1
    assert data[0]["average_interval_seconds"] is None

def test_historical_trends_multiple_elections(test_db, client, create_test_elections, create_test_polling_stations, create_test_votes, create_test_voters, create_test_candidates):
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"},
        {"id": 4, "name": "Active Voter 4", "email": "active4@example.com", "role": "voter"},
        {"id": 5, "name": "Active Voter 5", "email": "active5@example.com", "role": "voter"}
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True},
        {"user_id": 4, "has_voted": True},
        {"user_id": 5, "has_voted": False}
    ]
    create_test_voters(users_data, voters_data)

    # Arrange: Create multiple elections and a polling station.
    create_test_elections([
        {"id": 1, "name": "Election 2020"},
        {"id": 2, "name": "Election 2021"},
    ])
    create_test_candidates([
        {"id": 1, "name": "Candidate A", "party": "Group X", "bio": "Experienced leader.", "election_id": 1},
        {"id": 2, "name": "Candidate B", "party": "Group Y", "bio": "Visionary thinker.", "election_id": 1},
        {"id": 3, "name": "Candidate C", "party": "Group Z", "bio": "Innovative innovator.", "election_id": 1}
    ])
    create_test_polling_stations([
        {"id": 1, "name": "Station A", "location": "School", "election_id": 1, "capacity": 300},
    ])

    now = datetime.now(timezone.utc)
    # Votes for Election 2020, Station A
    create_test_votes([
        {"id": 1, "election_id": 1, "voter_id": 1, "candidate_id": 1, "polling_station_id": 1, "timestamp": now},
        {"id": 2, "election_id": 1, "voter_id": 2, "candidate_id": 1, "polling_station_id": 1, "timestamp": now + timedelta(seconds=60)},
    ])
    # Votes for Election 2021, Station A
    create_test_votes([
        {"id": 3, "election_id": 2, "voter_id": 3, "candidate_id": 1, "polling_station_id": 1, "timestamp": now + timedelta(days=365)},
        {"id": 4, "election_id": 2, "voter_id": 4, "candidate_id": 1, "polling_station_id": 1, "timestamp": now + timedelta(days=365, seconds=90)},
    ])

    # Act: Request historical trends for elections 1 and 2 filtered by polling station 1.
    response = client.get("/votes/analytics/historical_polling_station_trends?election_ids=1,2&polling_station_id=1")

    test_db.rollback()
    gc.collect()

    data = response.json()

    # Assert: Expect results for both elections.
    assert response.status_code == 200
    # Our results should have an entry for each election.
    election_ids_returned = {entry["election_id"] for entry in data}
    assert 1 in election_ids_returned
    assert 2 in election_ids_returned

def test_historical_trends_without_polling_station_filter(test_db, create_test_elections, create_test_polling_stations, create_test_votes, create_test_voters, create_test_candidates, client):
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"},
        {"id": 4, "name": "Active Voter 4", "email": "active4@example.com", "role": "voter"},
        {"id": 5, "name": "Active Voter 5", "email": "active5@example.com", "role": "voter"}
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True},
        {"user_id": 4, "has_voted": True},
        {"user_id": 5, "has_voted": False}
    ]
    create_test_voters(users_data, voters_data)

    # Arrange: Create elections and multiple polling stations.
    create_test_elections([
        {"id": 1, "name": "Election 2020"},
    ])
    create_test_candidates([
        {"id": 1, "name": "Candidate A", "party": "Group X", "bio": "Experienced leader.", "election_id": 1},
        {"id": 2, "name": "Candidate B", "party": "Group Y", "bio": "Visionary thinker.", "election_id": 1},
        {"id": 3, "name": "Candidate C", "party": "Group Z", "bio": "Innovative innovator.", "election_id": 1}
    ])
    create_test_polling_stations([
        {"id": 1, "name": "Station A", "location": "School", "election_id": 1, "capacity": 300},
        {"id": 2, "name": "Station B", "location": "Park", "election_id": 1, "capacity": 200},
    ])

    now = datetime.now(timezone.utc)
    # Votes for Election 2020, Station A and Station B.
    create_test_votes([
        {"id": 1, "election_id": 1, "voter_id": 1, "candidate_id": 1, "polling_station_id": 1, "timestamp": now},
        {"id": 2, "election_id": 1, "voter_id": 2, "candidate_id": 2, "polling_station_id": 2, "timestamp": now + timedelta(seconds=30)},
    ])

    # Act: Request historical trends for election 1 without providing a polling station ID.
    response = client.get("/votes/analytics/historical_polling_station_trends?election_ids=1")

    test_db.rollback()
    gc.collect()

    data = response.json()

    # Assert: The results should include entries for all polling stations.
    assert response.status_code == 200
    station_ids_returned = {entry["polling_station"]["id"] for entry in data}
    assert 1 in station_ids_returned
    assert 2 in station_ids_returned

def test_predictive_turnout_no_historical_data(test_db, client, create_test_elections):
    # Arrange: Create no past elections.
    create_test_elections([
        {"id": 1, "name": "Upcoming Election"}
    ])

    # Act: Request prediction for upcoming election with id=1.
    response = client.get("/votes/analytics/predictive_voter_turnout?upcoming_election_id=1")

    test_db.rollback()
    gc.collect()

    data = response.json()

    # Assert: No historical data implies prediction is None.
    assert response.status_code == 200
    assert data["predicted_turnout"] is None
    assert data["historical_turnouts"] == []

def test_predictive_turnout_single_historical_election(test_db, client, create_test_elections, create_test_votes, create_test_voters, create_test_candidates):
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"},
        {"id": 4, "name": "Active Voter 4", "email": "active4@example.com", "role": "voter"},
        {"id": 5, "name": "Active Voter 5", "email": "active5@example.com", "role": "voter"}
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True},
        {"user_id": 4, "has_voted": True},
        {"user_id": 5, "has_voted": False}
    ]
    create_test_voters(users_data, voters_data)
    # Arrange: Create one historical election.
    create_test_elections([
        {"id": 1, "name": "Election 1"},
        {"id": 2, "name": "Upcoming Election"}
    ])
    create_test_candidates([
        {"id": 1, "name": "Candidate A", "party": "Group X", "bio": "Experienced leader.", "election_id": 1},
        {"id": 2, "name": "Candidate B", "party": "Group Y", "bio": "Visionary thinker.", "election_id": 1},
        {"id": 3, "name": "Candidate C", "party": "Group Z", "bio": "Innovative innovator.", "election_id": 1}
    ])
    now = datetime.now(timezone.utc)
    # Create votes for election 1.
    create_test_votes([
        {"id": 1, "election_id": 1, "voter_id": 1, "candidate_id": 1, "timestamp": now},
        {"id": 2, "election_id": 1, "voter_id": 2, "candidate_id": 1, "timestamp": now + timedelta(seconds=60)},
    ])

    # Act: Request prediction for upcoming election (id=2).
    response = client.get("/votes/analytics/predictive_voter_turnout?upcoming_election_id=2")

    test_db.rollback()
    gc.collect()

    data = response.json()

    # Assert: With one historical election, the prediction is the turnout of that election.
    assert response.status_code == 200
    assert data["predicted_turnout"] == 2
    assert len(data["historical_turnouts"]) == 1

def test_predictive_turnout_multiple_historical_elections(test_db, client, create_test_elections, create_test_votes, create_test_voters, create_test_candidates):
    for i in range(220):
        create_test_voters([{
            "id": i + 1, 
            "name": "Active Voter" + str(i + 1), 
            "email": "active" + str(i + 1) + "@example.com", 
            "role": "voter"
        }], 
        [{
            "user_id": i + 1, 
            "has_voted": True
        }])
    # Arrange: Create multiple historical elections.
    create_test_elections([
        {"id": 1, "name": "Election 1"},
        {"id": 2, "name": "Election 2"},
        {"id": 3, "name": "Upcoming Election"}
    ])
    create_test_candidates([
        {"id": 1, "name": "Candidate A", "party": "Group X", "bio": "Experienced leader.", "election_id": 1},
        {"id": 2, "name": "Candidate B", "party": "Group Y", "bio": "Visionary thinker.", "election_id": 1},
        {"id": 3, "name": "Candidate C", "party": "Group Z", "bio": "Innovative innovator.", "election_id": 1}
    ])
    now = datetime.now(timezone.utc)
    # Votes for Election 1: 100 votes (simulate by count)
    for i in range(100):
        create_test_votes([{
            "election_id": 1,
            "voter_id": i + 1,
            "candidate_id": 1,
            "timestamp": now + timedelta(seconds=i)
        }])
    # Votes for Election 2: 120 votes.
    for i in range(120):
        create_test_votes([{
            "election_id": 2,
            "voter_id": i + 100 + 1,
            "candidate_id": 1,
            "timestamp": now + timedelta(seconds=i)
        }])

    # Act: Predict turnout for the upcoming election (id=3).
    response = client.get("/votes/analytics/predictive_voter_turnout?upcoming_election_id=3")

    test_db.rollback()
    gc.collect()

    data = response.json()

    # Assert:
    # Historical turnouts: Election 1 = 100, Election 2 = 120.
    # Average increase = (120 - 100) = 20.
    # So predicted turnout = 120 + 20 = 140.
    assert response.status_code == 200
    assert data["predicted_turnout"] == 140
    assert len(data["historical_turnouts"]) == 2

def test_anomalies_detection(test_db, client, create_test_elections, create_test_polling_stations, create_test_votes, create_test_voters, create_test_candidates):
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"},
        {"id": 4, "name": "Active Voter 4", "email": "active4@example.com", "role": "voter"},
        {"id": 5, "name": "Active Voter 5", "email": "active5@example.com", "role": "voter"}
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True},
        {"user_id": 4, "has_voted": True},
        {"user_id": 5, "has_voted": False}
    ]
    create_test_voters(users_data, voters_data)

    create_test_elections([
        {"id": 1, "name": "Election Anomaly Test"}
    ])
    create_test_candidates([
        {"id": 1, "name": "Candidate A", "party": "Group X", "bio": "Experienced leader.", "election_id": 1},
        {"id": 2, "name": "Candidate B", "party": "Group Y", "bio": "Visionary thinker.", "election_id": 1},
        {"id": 3, "name": "Candidate C", "party": "Group Z", "bio": "Innovative innovator.", "election_id": 1}
    ])
    create_test_polling_stations([
        {"id": 1, "name": "Station A", "location": "School", "election_id": 1, "capacity": 300}
    ])
    
    now = datetime.now(timezone.utc)
    # Create votes at Station A with just 5-second intervals (which is below our threshold of 10 seconds)
    create_test_votes([
        {"id": 1, "election_id": 1, "voter_id": 1, "candidate_id": 1, "polling_station_id": 1, "timestamp": now},
        {"id": 2, "election_id": 1, "voter_id": 2, "candidate_id": 1, "polling_station_id": 1, "timestamp": now + timedelta(seconds=5)},
        {"id": 3, "election_id": 1, "voter_id": 3, "candidate_id": 1, "polling_station_id": 1, "timestamp": now + timedelta(seconds=10)},
    ])
    
    # Act: Call the anomaly detection endpoint for election 1.
    response = client.get("/votes/analytics/anomalies?election_id=1")

    test_db.rollback()
    gc.collect()


    data = response.json()
    
    # Assert: Expect an anomaly to be flagged since the average interval (~5s) is below threshold.
    assert response.status_code == 200
    assert isinstance(data, list)
    assert len(data) > 0
    anomaly = data[0]
    assert "polling_station" in anomaly
    assert "anomaly" in anomaly
    assert "High vote rate" in anomaly["anomaly"]

def test_anomaly_detection_no_votes(test_db, client, create_test_elections, create_test_polling_stations):
    # Arrange: Create an election and its polling station but no votes.
    create_test_elections([
        {"id": 1, "name": "Election No Votes"}
    ])
    create_test_polling_stations([
        {"id": 1, "name": "Station No Votes", "location": "Library", "election_id": 1, "capacity": 100}
    ])

    # Act:
    response = client.get("/votes/analytics/anomalies?election_id=1")

    test_db.rollback()
    gc.collect()

    data = response.json()

    # Assert:
    assert response.status_code == 200
    assert data == []  # No votes means no anomalies.

def test_anomaly_detection_exact_threshold(test_db, client, create_test_elections, create_test_polling_stations, create_test_votes, create_test_voters, create_test_candidates):
    users_data = [
        {"id": 1, "name": "Active Voter 1", "email": "active1@example.com", "role": "voter"},
        {"id": 2, "name": "Active Voter 2", "email": "active2@example.com", "role": "voter"},
        {"id": 3, "name": "Active Voter 3", "email": "active3@example.com", "role": "voter"},
        {"id": 4, "name": "Active Voter 4", "email": "active4@example.com", "role": "voter"},
        {"id": 5, "name": "Active Voter 5", "email": "active5@example.com", "role": "voter"}
    ]
    voters_data = [
        {"user_id": 1, "has_voted": True},
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": True},
        {"user_id": 4, "has_voted": True},
        {"user_id": 5, "has_voted": False}
    ]
    create_test_voters(users_data, voters_data)
    # Arrange: Create an election and a polling station.
    create_test_elections([
        {"id": 1, "name": "Election Exact Threshold"}
    ])
    create_test_candidates([
        {"id": 1, "name": "Candidate A", "party": "Group X", "bio": "Experienced leader.", "election_id": 1},
        {"id": 2, "name": "Candidate B", "party": "Group Y", "bio": "Visionary thinker.", "election_id": 1},
        {"id": 3, "name": "Candidate C", "party": "Group Z", "bio": "Innovative innovator.", "election_id": 1}
    ])
    create_test_polling_stations([
        {"id": 1, "name": "Station Exact", "location": "Mall", "election_id": 1, "capacity": 200}
    ])
    
    now = datetime.now(timezone.utc)
    # Create three votes 10 seconds apart.
    create_test_votes([
        {"id": 1, "election_id": 1, "voter_id": 1, "candidate_id": 1, "polling_station_id": 1, "timestamp": now},
        {"id": 2, "election_id": 1, "voter_id": 2, "candidate_id": 1, "polling_station_id": 1, "timestamp": now + timedelta(seconds=10)},
        {"id": 3, "election_id": 1, "voter_id": 3, "candidate_id": 1, "polling_station_id": 1, "timestamp": now + timedelta(seconds=20)},
    ])
    # The average interval here is exactly 10 seconds.
    response = client.get("/votes/analytics/anomalies?election_id=1")

    test_db.rollback()
    gc.collect()

    data = response.json()
    
    # Assert: Since our anomaly condition is < 10 seconds, an interval exactly at 10 seconds should not be flagged.
    assert response.status_code == 200
    assert data == []  # No anomalies expected.