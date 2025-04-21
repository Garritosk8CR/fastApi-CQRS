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
        json={
            "name": "Test User",
            "email": "testuser@example.com",
            "password": "securepassword"
        }
    )
    assert response.status_code == 201
    assert response.json() == {"message": "User Test User registered successfully as a voter!"}


def test_duplicate_email_sign_up(test_db):
    # First registration
    client.post(
        "/users/sign-up",
        json={
            "name": "Test User",
            "email": "testuser@example.com",
            "password": "securepassword"
        }
    )
    # Attempt second registration with the same email
    response = client.post(
        "/users/sign-up",
        json={
            "name": "Another User",
            "email": "testuser@example.com",
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
    assert "value is not a valid email address" in response.json()["detail"][0]["msg"]

def test_missing_fields_sign_up(test_db):
    response = client.post(
        "/users/sign-up",
        json={
            "name": "Test User"
            # Missing email and password
        }
    )
    assert response.status_code == 422  # Unprocessable Entity
    assert response.json()["detail"][0]["loc"] == ["body", "email"]
    assert response.json()["detail"][1]["loc"] == ["body", "password"]


def test_successful_login(test_db):
    # Pre-create a user in the test database
    user = User(
        name="Test User",
        email="testuser@example.com",
        password=hash_password("securepassword")
    )
    test_db.add(user)
    test_db.commit()

    # Send a login request
    response = client.post(
        "/users/login",
        data={
            "email": "testuser@example.com",
            "password": "securepassword"
        }
    )

    # Verify the response
    assert response.status_code == 200
    json_response = response.json()
    assert "access_token" in json_response
    assert json_response["token_type"] == "bearer"

