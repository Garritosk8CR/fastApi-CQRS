import gc
from random import randint
import pytest
from fastapi.testclient import TestClient
from app.main import app  # Import the FastAPI instance from main.py
from app.infrastructure.database import Base, SessionLocal, engine
from app.infrastructure.models import User, Voter
from app.security import hash_password

# Create a TestClient for the FastAPI app
client = TestClient(app)

# Set up the test database
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

@pytest.fixture
def create_test_users(test_db):
    def _create_users(users_data):
        users = []
        for user_data in users_data:
            user = User(**user_data)
            test_db.add(user)
            users.append(user)
        test_db.commit()
        return users
    return _create_users

@pytest.fixture
def create_test_admins(test_db):
    def _create_admins(admins_data):
        admins = []
        for admin_data in admins_data:
            admin = User(**admin_data)
            test_db.add(admin)
            admins.append(admin)
        test_db.commit()
        return admins
    return _create_admins

@pytest.fixture
def create_test_data_statistics(test_db):
    def _create_data(users_data, voters_data):
        users = []
        voters = []

        # Create users
        for user_data in users_data:
            user = User(**user_data)
            test_db.add(user)
            users.append(user)

        test_db.flush()  # Flush to generate IDs

        # Create voters
        for voter_data in voters_data:
            voter = Voter(**voter_data)
            test_db.add(voter)
            voters.append(voter)

        test_db.commit()
        return users, voters
    return _create_data

def test_successful_sign_up(test_db):
    response = client.post(
        "/users/sign-up",
        data={
            "name": "Test User5",
            "email": "testuser5@example.com",
            "password": "securepassword"
        }
    )
    assert response.status_code == 200
    test_db.rollback()
    gc.collect()


def test_duplicate_email_sign_up(test_db):
    # First registration
    client.post(
        "/users/sign-up",
        data={
            "name": "Test User2",
            "email": "testuser2@example.com",
            "password": "securepassword"
        }
    )
    # Attempt second registration with the same email
    response = client.post(
        "/users/sign-up",
        data={
            "name": "Another User",
            "email": "testuser2@example.com",
            "password": "anotherpassword"
        }
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Email already exists!"}

def test_invalid_email_format(test_db):
    response = client.post(
        "/users/sign-up",
        json={
            "name": "Test User",
            "email": "not-an-email",
            "password": "securepassword"
        }
    )
    assert response.status_code == 422  # Unprocessable Entity
    assert "Field required" in response.json()["detail"][0]["msg"]

def test_missing_fields_sign_up(test_db):
    response = client.post(
        "/users/sign-up",
        json={
            "name": "Test User"
            # Missing email and password
        }
    )
    assert response.status_code == 422  # Unprocessable Entity

def test_login_sets_cookie(test_db):
    # Step 1: Create a user in the test database
    user = User(
        name="Test User",
        email="testuser@example.com",
        password=hash_password("securepassword")
    )
    test_db.add(user)
    test_db.commit()

    # Step 2: Send a login request
    response = client.post(
        "/users/login",
        data={"email": "testuser@example.com", "password": "securepassword"}
    )

    # Step 3: Assert the cookie contains the token
    assert client.cookies.get("access_token") is not None
    test_db.rollback()
    gc.collect()

def test_invalid_email_login(test_db):
    response = client.post(
        "/users/login",
        data={
            "email": "nonexistent@example.com",
            "password": "securepassword"
        }
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}

def test_wrong_password_login(test_db):
    response = client.post(
        "/users/login",
        data={
            "email": "testuser@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}

def test_missing_fields_login():
    response = client.post(
        "/users/login",
        data={
            "email": "testuser@example.com"
            # Missing password
        }
    )
    assert response.status_code == 422
    assert "password" in str(response.json()["detail"])

def test_invalid_form_data_login():
    response = client.post(
        "/users/login",
        data={
            "email": "not-an-email",
            "password": "securepassword"
        }
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}

def test_edit_user(test_db):
    # Create a test user
    user = User(name="Old Name", email="oldemail@example.com", password="oldpassword")
    test_db.add(user)
    test_db.commit()

    # Prepare the update data
    update_data = {
        "name": "New Name",
        "email": "newemail@example.com",
        "password": "newpassword"
    }

    # Send the request
    response = client.put(f"/users/{user.id}", json=update_data)

    # Verify the response
    assert response.status_code == 200
    assert response.json()["message"] == "User updated successfully!"
    assert response.json()["user"]["name"] == "New Name"
    assert response.json()["user"]["email"] == "newemail@example.com"
    test_db.rollback()
    gc.collect()

def test_edit_user_not_found(test_db):
    # Attempt to edit a non-existent user
    update_data = {
        "name": "New Name",
        "email": "newemail@example.com",
        "password": "newpassword"
    }

    response = client.put("/users/999", json=update_data)  # Assume user ID 999 does not exist
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"
    test_db.rollback()
    gc.collect()

def test_edit_user_invalid_email(test_db):
    # Create a test user
    user = User(name="Old Name", email="oldemail@example.com", password="oldpassword")
    test_db.add(user)
    test_db.commit()

    # Attempt to edit user with an invalid email
    update_data = {
        "name": "New Name",
        "email": "not-an-email",
        "password": "newpassword"
    }

    response = client.put(f"/users/{user.id}", json=update_data)
    assert response.status_code == 422  # Unprocessable Entity
    assert "value is not a valid email address" in response.json()["detail"][0]["msg"]
    test_db.rollback()
    gc.collect()

def test_edit_user_missing_fields(test_db):
    # Create a test user
    user = User(name="Older Name", email="olderemail@example.com", password="oldpassword")
    test_db.add(user)
    test_db.commit()

    # Attempt to edit user with missing name field
    update_data = {
        "email": "newemail@example.com",
        "password": "newpassword"
    }

    response = client.put(f"/users/{user.id}", json=update_data)
    assert response.status_code == 422  # Unprocessable Entity
    assert "Field required" in response.json()["detail"][0]["msg"]
    test_db.rollback()
    gc.collect()

def test_edit_user_no_changes(test_db):
    # Create a test user
    user = User(name="Oldy Name", email="oldyemail@example.com", password="oldpassword")
    test_db.add(user)
    test_db.commit()

    # Attempt to edit user with the same data
    update_data = {
        "name": "Oldy Name",
        "email": "oldyemail@example.com",
        "password": "oldpassword"
    }

    response = client.put(f"/users/{user.id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["message"] == "User updated successfully!"
    assert response.json()["user"]["name"] == "Oldy Name"
    assert response.json()["user"]["email"] == "oldyemail@example.com"
    assert response.json()["user"]["password"] == "oldpassword"
    test_db.rollback()
    gc.collect()

def test_edit_user_duplicate_email(test_db):
    # Create two test users
    user1 = User(name="User1", email="user1@example.com", password="password1")
    user2 = User(name="User2", email="user2@example.com", password="password2")
    test_db.add_all([user1, user2])
    test_db.commit()

    # Attempt to update user1's email to user2's email
    update_data = {
        "name": "User1 Updated",
        "email": "user2@example.com",
        "password": "password1"
    }

    response = client.put(f"/users/{user1.id}", json=update_data)
    assert response.status_code == 400  # Bad Request
    assert response.json()["detail"] == "Email already exists!"
    test_db.rollback()
    gc.collect()

def test_get_user_profile(test_db):
    # Step 1: Create a test user
    user = User(
        name="Test User",
        email="testuser555@example.com",
        password=hash_password("securepassword")
    )
    test_db.add(user)
    test_db.commit()

    # Step 2: Send a login request
    response = client.post(
        "/users/login",
        data={"email": "testuser555@example.com", "password": "securepassword"}
    )
    print(f"Access token: {client.cookies.get('access_token')}")
    # Step 3: Assert the cookie contains the token
    assert client.cookies.get("access_token") is not None
    cookies = {"access_token": client.cookies.get("access_token")}
    access_token = client.cookies.get("access_token")
    # Step 3: Make the request using the cookie
    profile_response = client.get(
        "users/users/profile", 
        headers={"Authorization": f"Bearer {access_token}"}, 
        cookies=cookies
    )
    # Step 4: Validate response
    print(f"Profile response: {profile_response.json()}")
    assert profile_response.status_code == 200
    assert profile_response.json()["user"]["name"] == "Test User"
    assert profile_response.json()["user"]["email"] == "testuser555@example.com"
    test_db.rollback()
    gc.collect()

def test_get_user_by_id_success(test_db):
    # Arrange: Create a test user
    user = User(
        name="Test User",
        email="test@example.com",
        password=hash_password("securepassword"),
        role="admin"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    # Act: Call the endpoint
    response = client.get(f"/users/{user.id}")

    # Assert: Verify the response
    assert response.status_code == 200
    assert response.json() == {
        "id": user.id,
        "name": "Test User",
        "email": "test@example.com",
        "role": "admin"
    }

    test_db.rollback()
    gc.collect()

def test_get_user_by_id_not_found(test_db):
    # Act: Call the endpoint with a non-existent user ID
    response = client.get("/users/999")

    # Assert: Verify the response
    assert response.status_code == 404
    assert response.json() == {"detail": "User with ID 999 not found."}

    test_db.rollback()
    gc.collect()

def test_list_admins_success(test_db, create_test_admins):
    # Arrange: Create some admin users
    admins_data = [
        {"name": "Admin User 1", "email": "admin1@example.com", "role": "admin"},
        {"name": "Admin User 2", "email": "admin2@example.com", "role": "admin"},
    ]
    create_test_admins(admins_data)

    # Act: Call the endpoint
    response = client.get("/users/admins/")

    print(f"Admins response: {response.json()}")
    # Assert: Verify the response
    assert response.status_code == 200
    assert response.json() == {
        "admins": [
            {"id": 1, "name": "Admin User 1", "email": "admin1@example.com"},
            {"id": 2, "name": "Admin User 2", "email": "admin2@example.com"}
        ]
    }
    test_db.rollback()
    gc.collect()

def test_list_admins_no_admins(test_db):
    # Act: Call the endpoint when no admins exist
    response = client.get("/users/admins/")

    # Assert: Verify the response
    assert response.status_code == 200
    assert response.json() == {"admins": []}

    test_db.rollback()
    gc.collect()

def test_list_admins_pagination(test_db, create_test_admins):
    # Arrange: Create multiple admin users
    admins_data = [
        {"id": 1, "name": "Admin User 1", "email": "admin1@example.com", "role": "admin"},
        {"id": 2, "name": "Admin User 2", "email": "admin2@example.com", "role": "admin"},
        {"id": 3, "name": "Admin User 3", "email": "admin3@example.com", "role": "admin"},
    ]
    create_test_admins(admins_data)

    # Act: Call the endpoint with pagination parameters (page=1, page_size=2)
    response = client.get("/users/admins/?page=1&page_size=2")

    print(f"Admins response: {response.json()}")

    # Assert: Verify the response for the first page
    assert response.status_code == 200
    assert response.json() == {
        "admins": [
            {"id": 1, "name": "Admin User 1", "email": "admin1@example.com"},
            {"id": 2, "name": "Admin User 2", "email": "admin2@example.com"}
        ]
    }

    # Act: Call the endpoint for the second page (page=2, page_size=2)
    response = client.get("/users/admins/?page=2&page_size=2")

    # Assert: Verify the response for the second page
    assert response.status_code == 200
    assert response.json() == {
        "admins": [
            {"id": 3, "name": "Admin User 3", "email": "admin3@example.com"}
        ]
    }

    test_db.rollback()
    gc.collect()

def test_users_by_role_success(test_db, create_test_users):
    # Arrange: Create some users with different roles
    users_data = [
        {"id": 1, "name": "Admin User", "email": "admin@example.com", "role": "admin"},
        {"id": 2, "name": "Voter User 1", "email": "voter1@example.com", "role": "voter"},
        {"id": 3, "name": "Voter User 2", "email": "voter2@example.com", "role": "voter"},
    ]
    create_test_users(users_data)

    # Act: Call the endpoint to filter by role "voter"
    response = client.get("/users/by-role/?role=voter")

    # Assert: Verify the response
    assert response.status_code == 200
    assert response.json() == {
        "users": [
            {"id": 2, "name": "Voter User 1", "email": "voter1@example.com", "role": "voter"},
            {"id": 3, "name": "Voter User 2", "email": "voter2@example.com", "role": "voter"},
        ]
    }

    test_db.rollback()
    gc.collect()

def test_users_by_role_no_users(test_db):
    # Act: Call the endpoint to filter by role "nonexistent_role"
    response = client.get("/users/by-role/?role=nonexistent_role")

    # Assert: Verify the response
    assert response.status_code == 200
    assert response.json() == {"users": []}

    test_db.rollback()
    gc.collect()

def test_users_by_role_pagination(test_db, create_test_users):
    # Arrange: Create multiple users with the same role
    users_data = [
        {"id": 1, "name": "Admin User 1", "email": "admin1@example.com", "role": "admin"},
        {"id": 2, "name": "Admin User 2", "email": "admin2@example.com", "role": "admin"},
        {"id": 3, "name": "Admin User 3", "email": "admin3@example.com", "role": "admin"},
    ]
    create_test_users(users_data)

    # Act: Call the endpoint with pagination parameters (page=1, page_size=2)
    response = client.get("/users/by-role/?role=admin&page=1&page_size=2")

    # Assert: Verify the response for the first page
    assert response.status_code == 200
    assert response.json() == {
        "users": [
            {"id": 1, "name": "Admin User 1", "email": "admin1@example.com", "role": "admin"},
            {"id": 2, "name": "Admin User 2", "email": "admin2@example.com", "role": "admin"},
        ]
    }

    # Act: Call the endpoint for the second page (page=2, page_size=2)
    response = client.get("/users/by-role/?role=admin&page=2&page_size=2")

    # Assert: Verify the response for the second page
    assert response.status_code == 200
    assert response.json() == {
        "users": [
            {"id": 3, "name": "Admin User 3", "email": "admin3@example.com", "role": "admin"},
        ]
    }

    test_db.rollback()
    gc.collect()

def test_statistics_valid_calculation(test_db, create_test_data_statistics):
    # Arrange: Create users and voters
    users_data = [
        {"id": 1, "name": "Admin User", "email": "admin@example.com", "role": "admin"},
        {"id": 2, "name": "Voter User 1", "email": "voter1@example.com", "role": "voter"},
        {"id": 3, "name": "Voter User 2", "email": "voter2@example.com", "role": "voter"},
    ]
    voters_data = [
        {"user_id": 2, "has_voted": True},
        {"user_id": 3, "has_voted": False},
    ]
    create_test_data_statistics(users_data, voters_data)

    # Act: Call the endpoint
    response = client.get("/users/statistics/")

    # Assert: Verify the response
    print(f"Statistics response: {response.json()}")
    assert response.status_code == 200
    assert response.json() == {
        "total_users": 3,
        "total_voters": 2,
        "voting_percentage": 50.0,
        "roles": [
            {"role": "admin", "count": 1},
            {"role": "voter", "count": 2},
        ],
    }

    test_db.rollback()
    gc.collect()