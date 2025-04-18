import uvicorn
from app.interfaces.voter_controller import app
from app.infrastructure.database import engine, Base

# Create tables in the database
Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
