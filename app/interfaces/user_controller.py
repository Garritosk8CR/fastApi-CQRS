from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.application.handlers import RegisterUserHandler
from app.application.commands import UserSignUp

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/sign-up", status_code=201)
async def sign_up(user_data: UserSignUp, db: Session = Depends(get_db)):
    handler = RegisterUserHandler()
    try:
        result = handler.handle(user_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
