import uvicorn
from app.infrastructure.database import engine, Base
import sqlalchemy
from fastapi import FastAPI
from app.interfaces.voter_controller import router as voter_router
from app.interfaces.election_controller import router as election_router

app = FastAPI()

# Include the voter router
app.include_router(voter_router, prefix="/voter", tags=["Voters"])
app.include_router(election_router, prefix="/elections", tags=["Elections"])
print(app.openapi())
# Create tables in the database
Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
