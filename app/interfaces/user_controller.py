from datetime import timedelta
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.infrastructure.database import get_db
from app.application.handlers import AuthCommandHandler, RegisterUserHandler
from app.application.commands import LoginUserCommand, UserSignUp
from app.infrastructure.models import User
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/users", tags=["Users"])


templates = Jinja2Templates(directory="app/templates")  # Path to your templates folder

@router.get("/sign-up", response_class=HTMLResponse)
async def render_sign_up_form(request: Request):
    is_logged_in = request.cookies.get("access_token") is not None  # Check if token exists
    return templates.TemplateResponse("sign_up.html", {"request": request, "is_logged_in": is_logged_in})

@router.get("/login", response_class=HTMLResponse)
async def render_login_form(request: Request):
    is_logged_in = request.cookies.get("access_token") is not None  # Check if token exists
    return templates.TemplateResponse("login.html", {"request": request, "is_logged_in": is_logged_in})

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
    
@router.post("/login")
async def login(command: LoginUserCommand):
    print(f"Logging in user with email: {command.email}")

    # Dispatch the command to the handler
    auth_command_handler = AuthCommandHandler()
    access_token = auth_command_handler.handle(command)
    print("Token created")

    # Set cookie and redirect
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=1800
    )
    return response


