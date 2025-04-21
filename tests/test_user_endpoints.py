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



