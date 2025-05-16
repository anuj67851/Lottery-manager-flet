import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List, Any

from app.core.models import User
from app.constants import EMPLOYEE_ROLE # Use constant
from app.core.exceptions import UserNotFoundError, DatabaseError, ValidationError # Import custom exceptions

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

def get_users_by_roles(db: Session, roles: List[str]) -> list[type[User]]:
    return db.query(User).filter(User.role.in_(roles)).all()

def create_user(db: Session, username: str, password: str, role: str = EMPLOYEE_ROLE, created_date: datetime = datetime.date.today()) -> User:
    """
    Create a new user.
    Raises:
        ValidationError: If username or password is not provided.
        DatabaseError: If the user could not be created (e.g., username exists).
    """
    if not username:
        raise ValidationError("Username is required for creating a user.")
    if not password:
        raise ValidationError("Password is required for creating a user.")

    existing_user = get_user_by_username(db, username)
    if existing_user:
        raise DatabaseError(f"User with username '{username}' already exists.")

    try:
        user = User(username=username, role=role, created_date=created_date)
        user.set_password(password)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError: # Should be caught by pre-check, but as a fallback
        db.rollback()
        raise DatabaseError(f"User with username '{username}' already exists.")
    except Exception as e:
        db.rollback()
        # Log the original exception e for debugging
        raise DatabaseError(f"Could not create user: An unexpected error occurred.")


def update_user(db: Session, user_id: int, username: Optional[str] = None,
                password: Optional[str] = None, role: Optional[str] = None) -> User:
    """
    Update a user.
    Raises:
        UserNotFoundError: If the user with user_id is not found.
        DatabaseError: If the update fails.
    """
    user = get_user_by_id(db, user_id)
    if not user:
        raise UserNotFoundError(f"User with ID {user_id} not found.")

    try:
        if username:
            # Check if new username already exists for another user
            if db.query(User).filter(User.username == username, User.id != user_id).first():
                raise DatabaseError(f"Username '{username}' is already taken by another user.")
            user.username = username
        if password:
            user.set_password(password)
        if role:
            user.role = role
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        db.rollback()
        raise DatabaseError(f"Could not update user: Username '{username}' may already exist.")
    except Exception as e:
        db.rollback()
        raise DatabaseError(f"Could not update user: An unexpected error occurred.")


def delete_user(db: Session, user_id: int) -> bool:
    """
    Delete a user.
    Raises:
        UserNotFoundError: If the user with user_id is not found.
        DatabaseError: If deletion fails.
    """
    user = get_user_by_id(db, user_id)
    if not user:
        raise UserNotFoundError(f"User with ID {user_id} not found.")
    try:
        db.delete(user)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise DatabaseError(f"Could not delete user: An unexpected error occurred.")

def any_users_exist(db: Session) -> bool:
    return db.query(User).first() is not None