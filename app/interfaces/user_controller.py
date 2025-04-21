from datetime import timedelta
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.infrastructure.database import get_db
from app.application.handlers import RegisterUserHandler
from app.application.commands import UserSignUp
from app.infrastructure.models import User
from app.security import create_access_token, verify_password

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
    
@router.post("/login", status_code=200)
async def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Retrieve user by email
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Verify the password
    if not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Create the JWT token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}

