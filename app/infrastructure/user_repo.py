from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
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

    def get_user_by_id(self, user_id: int) -> User:
        return self.db.query(User).filter(User.id == user_id).first()
    
    def update_user(self, user_id: int, updated_data: dict) -> User:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        for key, value in updated_data.items():
            setattr(user, key, value)
        
        try:
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError as e:
            self.db.rollback()  # Rollback the session to prevent partial updates
            raise ValueError("Email already exists!") from e
    
    def get_users(self, page: int, page_size: int):
        offset = (page - 1) * page_size
        return self.db.query(User).offset(offset).limit(page_size).all()
    
    def update_role(self, user: User, new_role: str):
        user.role = new_role
        self.db.commit()
        self.db.refresh(user)
        print(f"Role updated for user {user.id}: {user.role}")

    def get_users_by_role(self, role: str, page: int, page_size: int):
        print(f"Getting users with role '{role}'")
        offset = (page - 1) * page_size
        return self.db.query(User).filter(User.role == role).offset(offset).limit(page_size).all()
    
    def get_total_users(self):
        return self.db.query(func.count(User.id)).scalar()
    
    def get_users_by_roles(self):
        results = (
            self.db.query(User.role, func.count(User.id))
            .group_by(User.role)
            .all()
        )
        # Convert tuples to dictionaries
        return [{"role": role, "count": count} for role, count in results]


