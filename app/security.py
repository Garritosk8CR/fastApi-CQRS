from datetime import datetime, timezone,timedelta
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import JWTError, jwt
from app.config import SECRET_KEY, ALGORITHM
from app.infrastructure.database import SessionLocal
from app.infrastructure.user_repo import UserRepository

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta=None):
    to_encode = data.copy()
    if expires_delta:
        to_encode.update({"exp": datetime.now(timezone.utc) + expires_delta})

    else:
        to_encode.update({"exp": datetime.now(timezone.utc) + timedelta(minutes=15)})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(request: Request):
    try:
        # Check if the token is present in cookies
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Missing token")

        # Decode the token
        payload = jwt.decode(token.split(" ")[1], SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return email
    except (JWTError, IndexError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def get_current_complete_user( request: Request,token: str = Depends(oauth2_scheme)):
    with SessionLocal() as db:
        try:
            # Check if the token is present in cookies
            print("Cookies received:", request.cookies)
            cookie_token = request.cookies.get("access_token")
            print(f"Cookie token: {cookie_token}")
            auth_header_token = token if token else None 
            print(f"Auth header token: {auth_header_token}")
            final_token = cookie_token or auth_header_token
            print(f"Final token: {final_token}")
            if not final_token:
                raise HTTPException(status_code=401, detail="Authentication required")

            # Decode the token
            payload = jwt.decode(final_token.split(" ")[1], SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            user_repository = UserRepository(db)

            # Retrieve user by email
            
            if email is None:
                raise HTTPException(status_code=401, detail="Invalid token")
            user = user_repository.get_user_by_email(email)
            return user
        except (JWTError, IndexError):
            raise HTTPException(status_code=401, detail="Invalid or expired token")