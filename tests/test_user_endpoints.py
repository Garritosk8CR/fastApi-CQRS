import pytest
from fastapi.testclient import TestClient
from app.main import app  # Import the FastAPI instance from main.py
from app.infrastructure.database import Base, engine

# Create a TestClient for the FastAPI app
client = TestClient(app)

# Set up the test database
@pytest.fixture(scope="module")
def test_db():
    # Ensure the database schema is created
    Base.metadata.create_all(bind=engine)
    yield
    # Clean up the database after tests
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
