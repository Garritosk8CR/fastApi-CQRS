from app.infrastructure.models import User
from app.utils.password_utils import hash_password


class UserRepository:
    def __init__(self, db):
        self.db = db

    def create_user(self, name: str, email: str, password: str, role: str = "voter"):
        hashed_password = hash_password(password)  # Hash the password here
        new_user = User(name=name, email=email, password=hashed_password, role=role)
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        return new_user

    def get_user_by_email(self, email: str) -> User:
        return self.db.query(User).filter(User.email == email).first()
