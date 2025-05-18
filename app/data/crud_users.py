from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List

from app.core.models import User
from app.constants import EMPLOYEE_ROLE # Use constant
from app.core.exceptions import UserNotFoundError, DatabaseError, ValidationError # Import custom exceptions

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

def get_users_by_roles(db: Session, roles: List[str]) -> List[User]: # Return List[User]
    return db.query(User).filter(User.role.in_(roles)).order_by(User.username).all() # Added ordering

def get_all_users(db: Session) -> List[User]: # Return List[User]
    return db.query(User).order_by(User.username).all() # Added ordering


def create_user(db: Session, username: str, password: str, role: str = EMPLOYEE_ROLE) -> User:
    """
    Create a new user.
    Raises:
        ValidationError: If username or password is not provided.
        DatabaseError: If the user could not be created (e.g., username exists).
    """
    if not username:
        raise ValidationError("Username is required for creating a user.")
    if not password: # Password validation (e.g. length) should be in service or model if complex
        raise ValidationError("Password is required for creating a user.")
    if not role:
        raise ValidationError("Role is required for creating a user.")


    existing_user = get_user_by_username(db, username)
    if existing_user:
        raise DatabaseError(f"User with username '{username}' already exists.")

    try:
        # created_date is handled by SQLAlchemy model default
        user = User(username=username, role=role)
        user.set_password(password) # Hash password
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError: # Should be caught by pre-check, but as a fallback
        db.rollback()
        # This typically means username unique constraint was violated by a concurrent transaction
        raise DatabaseError(f"User with username '{username}' already exists (IntegrityError).")
    except Exception as e:
        db.rollback()
        # Log the original exception e for debugging
        raise DatabaseError(f"Could not create user '{username}': An unexpected error occurred: {e}")


def update_user(db: Session, user_id: int, username: Optional[str] = None,
                password: Optional[str] = None, role: Optional[str] = None, is_active: Optional[bool] = None) -> User:
    """
    Update a user. Can also update is_active status.
    Raises:
        UserNotFoundError: If the user with user_id is not found.
        DatabaseError: If the update fails.
        ValidationError: If new username is empty (if provided).
    """
    user = get_user_by_id(db, user_id)
    if not user:
        raise UserNotFoundError(f"User with ID {user_id} not found.")

    updated = False
    try:
        if username is not None:
            if not username.strip():
                raise ValidationError("Username cannot be empty.")
            # Check if new username already exists for another user
            if username != user.username and db.query(User).filter(User.username == username, User.id != user_id).first():
                raise DatabaseError(f"Username '{username}' is already taken by another user.")
            user.username = username
            updated = True
        if password: # Only update password if a new one is provided and not empty
            user.set_password(password)
            updated = True
        if role:
            user.role = role
            updated = True
        if is_active is not None:
            user.is_active = is_active
            updated = True

        if updated:
            db.commit()
            db.refresh(user)
        return user
    except IntegrityError: # e.g. if unique constraint on username violated by concurrent transaction
        db.rollback()
        # username check should ideally prevent this, but good to have
        raise DatabaseError(f"Could not update user {user.username}: Username conflict (IntegrityError).")
    except Exception as e:
        db.rollback()
        raise DatabaseError(f"Could not update user {user.username}: An unexpected error occurred: {e}")


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
        username_deleted = user.username # For logging or messages
        db.delete(user)
        db.commit()
        print(f"User '{username_deleted}' (ID: {user_id}) deleted successfully.") # Keep for now, or use logging
        return True
    except Exception as e:
        db.rollback()
        raise DatabaseError(f"Could not delete user with ID {user_id}: An unexpected error occurred: {e}")

def any_users_exist(db: Session) -> bool:
    return db.query(User.id).first() is not None # Query for id is slightly more efficient