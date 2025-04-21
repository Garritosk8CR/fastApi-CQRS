from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt
from app.config import SECRET_KEY, ALGORITHM

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta=None):
    to_encode = data.copy()
    if expires_delta:
        to_encode.update({"exp": datetime.now(datetime.timezone.utc) + expires_delta})
    else:
        to_encode.update({"exp": datetime.now(datetime.timezone.utc) + timedelta(minutes=15)})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
