from fastapi.responses import HTMLResponse
import uvicorn
from app.application.commands import CastVoteCommand, RegisterVoterCommand
from app.application.handlers import command_bus
from app.application.query_bus import query_bus
from app.application.queries import GetAllElectionsQuery, GetElectionDetailsQuery, GetElectionResultsQuery, GetVotingPageDataQuery
from app.infrastructure.database import engine, Base
from fastapi import Depends, FastAPI, HTTPException, Request
from app.interfaces.voter_controller import router as voter_router
from app.interfaces.election_controller import router as election_router
from app.interfaces.user_controller import router as user_router
from app.interfaces.polling_station_controller import router as polling_station_router
from app.interfaces.audit_log_controller import router as audit_log_router
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.security import get_current_user

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Include the voter router
app.include_router(election_router, prefix="/elections", tags=["Elections"])
app.include_router(voter_router, prefix="/voters", tags=["Voters"])
app.include_router(user_router)
app.include_router(polling_station_router)
app.include_router(audit_log_router)


# Create tables in the database
Base.metadata.create_all(bind=engine)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, current_user: str = Depends(get_current_user)):
    query = GetAllElectionsQuery()
    elections = query_bus.handle(query)  # Dispatch the query to the handler
    is_logged_in = request.cookies.get("access_token") is not None  # Check if token exists
    # Pass elections to the template
    return templates.TemplateResponse("home.html", {"request": request, "elections": elections, "is_logged_in": is_logged_in})

@app.get("/vote", response_class=HTMLResponse)
async def cast_vote_page(request: Request, current_user: str = Depends(get_current_user)):
    query = GetVotingPageDataQuery()
    try:
        page_data = query_bus.handle(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
    is_logged_in = request.cookies.get("access_token") is not None  # Check if token exists
    return templates.TemplateResponse(
        "vote.html",
        {"request": request, "voters": page_data["voters"], "elections": page_data["elections"], "is_logged_in": is_logged_in},
    )


@app.get("/register", response_class=HTMLResponse)
async def register_voter_page(request: Request):
    is_logged_in = request.cookies.get("access_token") is not None  # Check if token exists
    return templates.TemplateResponse("register.html", {"request": request, "is_logged_in": is_logged_in})

@app.get("/voters/register", response_class=HTMLResponse)
async def register_voter_page(request: Request):
    is_logged_in = request.cookies.get("access_token") is not None  # Check if token exists
    return templates.TemplateResponse("register_voter.html", {"request": request, "is_logged_in": is_logged_in})

@app.get("/elections/create", response_class=HTMLResponse)
async def create_election_page(request: Request, current_user: str = Depends(get_current_user)):
    is_logged_in = request.cookies.get("access_token") is not None  # Check if token exists
    return templates.TemplateResponse("create_election.html", {"request": request, "is_logged_in": is_logged_in})

@app.get("/results/{election_id}", response_class=HTMLResponse)
async def get_results(request: Request, election_id: int, current_user: str = Depends(get_current_user)):
    is_logged_in = request.cookies.get("access_token") is not None  # Check if token exists
    query = GetElectionResultsQuery(election_id=election_id)  # Now using dynamic election_id
    try:
        results = query_bus.handle(query)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

    # Pass the results to the template
    return templates.TemplateResponse("results.html", {"request": request, "results": results, "is_logged_in": is_logged_in})



@app.get("/elections/{election_id}", response_class=HTMLResponse)
async def election_details(election_id: int, request: Request, current_user: str = Depends(get_current_user)):
    query = GetElectionDetailsQuery(election_id)
    try:
        election_data = query_bus.handle(query)  # Dispatch the query to the handler
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

    is_logged_in = request.cookies.get("access_token") is not None  # Check if token exists
    # Pass the data to the template
    return templates.TemplateResponse("election.html", {"request": request, "election": election_data, "is_logged_in": is_logged_in})

@app.post("/voters/{voter_id}/elections/{election_id}/vote/", response_class=HTMLResponse)
async def cast_vote(voter_id: int, election_id: int, request: Request):
    form_data = await request.form()
    candidate = form_data["candidate"]

    # Dispatch the command with both voter_id and election_id
    command = CastVoteCommand(voter_id=voter_id, election_id=election_id, candidate=candidate)
    try:
        result = command_bus.handle(command)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

    # Render the confirmation template
    return templates.TemplateResponse(
        "confirmation.html",
        {"request": request, "candidate": result["candidate"], "election_name": result["election_name"]},
    )

@app.post("/register/", response_class=HTMLResponse)
async def register_voter(request: Request):
    request_data = await request.json()  # Expect JSON input
    voter_id = int(request_data["voter_id"])  # Extract values from JSON
    name = request_data["name"]

    command = RegisterVoterCommand(voter_id=voter_id, name=name)
    try:
        new_voter = command_bus.handle(command)
    except ValueError as e:
        return templates.TemplateResponse(
            "register.html", {"request": request, "error": str(e)}
        )

    return templates.TemplateResponse(
        "confirmation.html",
        {"request": request, "candidate": name, "election_name": "Registration", "voter": new_voter},
    )






if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
