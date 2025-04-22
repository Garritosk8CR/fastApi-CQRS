import pytest
from fastapi.testclient import TestClient
from app.main import app  # Import the FastAPI instance from main.py
from app.infrastructure.database import Base, SessionLocal, engine
from app.infrastructure.models import User
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
    profile_response = client.get("users/users/profile", headers={"Authorization": f"Bearer {access_token}"}, cookies=cookies)
    # Step 4: Validate response
    assert profile_response.status_code == 200
    assert profile_response.json()["user"]["name"] == "Test User"
    assert profile_response.json()["user"]["email"] == "testuser555@example.com"

