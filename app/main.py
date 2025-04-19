from fastapi.responses import HTMLResponse
import uvicorn
from app.application.commands import RegisterVoterCommand
from app.application.handlers import CommandBus
from app.application.query_bus import query_bus
from app.application.queries import GetAllElectionsQuery
from app.infrastructure.database import SessionLocal, engine, Base, get_db
import sqlalchemy
from sqlalchemy.orm import Session
from fastapi import Depends, FastAPI, HTTPException, Request
from app.infrastructure.election_repo import ElectionRepository
from app.infrastructure.models import Election
from app.infrastructure.voter_repo import VoterRepository
from app.interfaces.voter_controller import router as voter_router
from app.interfaces.election_controller import router as election_router
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Include the voter router
app.include_router(voter_router, prefix="/voters", tags=["Voters"])
app.include_router(election_router, prefix="/elections", tags=["Elections"])

# Create tables in the database
Base.metadata.create_all(bind=engine)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    query = GetAllElectionsQuery()
    elections = query_bus.handle(query)  # Dispatch the query to the handler
    
    # Pass elections to the template
    return templates.TemplateResponse("home.html", {"request": request, "elections": elections})

app.get("/elections/{election_id}", response_class=HTMLResponse)
async def election_details(election_id: int, request: Request, db: Session = Depends(get_db)):
    election = db.query(Election).filter(Election.id == election_id).first()
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
    election_data = {
        "id": election.id,
        "name": election.name,
        "candidates": election.candidates.split(",")
    }
    return templates.TemplateResponse("election.html", {"request": request, "election": election_data})

@app.post("/voters/{voter_id}/vote/", response_class=HTMLResponse)
async def cast_vote(voter_id: int, request: Request, db: Session = Depends(get_db)):
    form_data = await request.form()
    candidate = form_data["candidate"]

    voter_repo = VoterRepository(db)
    election_repo = ElectionRepository(db)

    voter = voter_repo.get_voter_by_id(voter_id)
    if not voter:
        raise HTTPException(status_code=404, detail="Voter not found")
    if voter.has_voted:
        raise HTTPException(status_code=400, detail="Voter has already voted")

    election = election_repo.get_election_by_id(1)  # Assuming election_id is 1
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")

    election.increment_vote(candidate)
    voter.has_voted = True
    db.commit()

    return templates.TemplateResponse(
        "confirmation.html",
        {"request": request, "candidate": candidate, "election_name": election.name},
    )

@app.get("/results", response_class=HTMLResponse)
async def get_results(request: Request, db: Session = Depends(get_db)):
    election = db.query(Election).filter(Election.id == 1).first()  # Assuming election ID = 1
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")

    results = {candidate: vote for candidate, vote in zip(election.candidates.split(","), election.votes.split(","))}
    return templates.TemplateResponse("results.html", {"request": request, "results": results})

@app.get("/register", response_class=HTMLResponse)
async def register_voter_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/voters/register", response_class=HTMLResponse)
async def register_voter_page(request: Request):
    return templates.TemplateResponse("register_voter.html", {"request": request})

@app.post("/register/", response_class=HTMLResponse)
async def register_voter(request: Request):
    form_data = await request.form()
    voter_id = int(form_data["voter_id"])
    name = form_data["name"]

    command = RegisterVoterCommand(voter_id=voter_id, name=name)
    try:
       new_voter = CommandBus.handle(command)
    except ValueError as e:
        return templates.TemplateResponse(
            "register.html", {"request": request, "error": str(e)}
        )

    return templates.TemplateResponse(
        "confirmation.html",
        {"request": request, "candidate": name, "election_name": "Registration", "voter": new_voter},
    )

# @app.post("/register/", response_class=HTMLResponse)
# async def register_voter(request: Request, db: Session = Depends(get_db)):
#     form_data = await request.form()
#     voter_id = int(form_data["voter_id"])
#     name = form_data["name"]

#     voter_repo = VoterRepository(db)
#     if voter_repo.get_voter_by_id(voter_id):
#         return templates.TemplateResponse(
#             "register.html",
#             {"request": request, "error": "Voter ID already exists! Try a different ID."}
#         )

#     # Register voter
#     voter_repo.create_voter(voter_id=voter_id, name=name)
#     db.commit()

#     return templates.TemplateResponse(
#         "confirmation.html",
#         {"request": request, "candidate": name, "election_name": "Registration"},
#     )

@app.get("/elections/create", response_class=HTMLResponse)
async def create_election_page(request: Request):
    return templates.TemplateResponse("create_election.html", {"request": request})





if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
