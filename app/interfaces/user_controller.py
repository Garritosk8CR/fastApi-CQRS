from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.application.handlers import RegisterUserHandler
from app.application.commands import UserSignUp

router = APIRouter(prefix="/users", tags=["Users"])


templates = Jinja2Templates(directory="app/templates")  # Path to your templates folder

@router.get("/sign-up", response_class=HTMLResponse)
async def render_sign_up_form(request: Request):
    return templates.TemplateResponse("sign_up.html", {"request": request})

from fastapi import Form

@router.post("/sign-up", status_code=201)
async def sign_up(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    handler = RegisterUserHandler()
    try:
        # Create a dictionary to simulate the original UserSignUp object
        user_data = {"name": name, "email": email, "password": password}
        result = handler.handle(user_data)
        return RedirectResponse(url="/users/login", status_code=302)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

