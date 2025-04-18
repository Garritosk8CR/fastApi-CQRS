import uvicorn
from infrastructure.database import engine, Base
import sqlalchemy
from fastapi import FastAPI
from interfaces.voter_controller import router as voter_router

app = FastAPI()

# Include the voter router
app.include_router(voter_router, prefix="/voter", tags=["Voters"])

# Create tables in the database
Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
