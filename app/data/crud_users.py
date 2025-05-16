"""
CRUD operations for User model.

This module provides functions to create, read, update, and delete users
in the database.
"""
from sqlalchemy.orm import Session
from typing import Optional, List, Tuple

from app.core.models import User

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """
    Get a user by ID.

    Args:
        db (Session): The database session.
        user_id (int): The ID of the user to retrieve.

    Returns:
        Optional[User]: The user if found, None otherwise.
    """
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """
    Get a user by username.

    Args:
        db (Session): The database session.
        username (str): The username of the user to retrieve.

    Returns:
        Optional[User]: The user if found, None otherwise.
    """
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, username: str, password: str, role: str = "employee") -> User:
    """
    Create a new user.

    Args:
        db (Session): The database session.
        username (str): The username for the new user.
        password (str): The password for the new user.
        role (str, optional): The role for the new user. Defaults to "employee".

    Returns:
        User: The created user.
    """
    user = User(username=username, role=role)
    user.set_password(password)

    db.add(user)
    db.commit()
    db.refresh(user)

    return user

def update_user(db: Session, user_id: int, username: Optional[str] = None, 
                password: Optional[str] = None, role: Optional[str] = None) -> Optional[User]:
    """
    Update a user.

    Args:
        db (Session): The database session.
        user_id (int): The ID of the user to update.
        username (Optional[str], optional): The new username. Defaults to None.
        password (Optional[str], optional): The new password. Defaults to None.
        role (Optional[str], optional): The new role. Defaults to None.

    Returns:
        Optional[User]: The updated user if found, None otherwise.
    """
    user = get_user_by_id(db, user_id)
    if not user:
        return None

    if username:
        user.username = username
    if password:
        user.set_password(password)
    if role:
        user.role = role

    db.commit()
    db.refresh(user)

    return user

def delete_user(db: Session, user_id: int) -> bool:
    """
    Delete a user.

    Args:
        db (Session): The database session.
        user_id (int): The ID of the user to delete.

    Returns:
        bool: True if the user was deleted, False otherwise.
    """
    user = get_user_by_id(db, user_id)
    if not user:
        return False

    db.delete(user)
    db.commit()

    return True

def any_users_exist(db: Session) -> bool:
    """
    Check if any users exist in the database.

    Args:
        db (Session): The database session.

    Returns:
        bool: True if at least one user exists, False otherwise.
    """
    return db.query(User).first() is not None
