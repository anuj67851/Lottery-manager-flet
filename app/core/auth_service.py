"""
Authentication service for the application.

This module provides functions to authenticate users and manage user sessions.
"""
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.data.crud_users import get_user_by_username
from app.core.models import User

class AuthService:
    """
    Service for user authentication and session management.
    """
    
    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Tuple[bool, Optional[User], Optional[str]]:
        """
        Authenticate a user with username and password.
        
        Args:
            db (Session): The database session.
            username (str): The username to authenticate.
            password (str): The password to authenticate.
            
        Returns:
            Tuple[bool, Optional[User], Optional[str]]: A tuple containing:
                - bool: True if authentication was successful, False otherwise.
                - Optional[User]: The authenticated user if successful, None otherwise.
                - Optional[str]: An error message if authentication failed, None otherwise.
        """
        # Check if username is provided
        if not username:
            return False, None, "Username is required"
        
        # Check if password is provided
        if not password:
            return False, None, "Password is required"
        
        # Get user by username
        user = get_user_by_username(db, username)
        
        # Check if user exists
        if not user:
            return False, None, "Invalid username or password"
        
        # Check if password is correct
        if not user.check_password(password):
            return False, None, "Invalid username or password"
        
        # Authentication successful
        return True, user, None
    
    @staticmethod
    def get_user_role(user: User) -> str:
        """
        Get the role of a user.
        
        Args:
            user (User): The user to get the role for.
            
        Returns:
            str: The role of the user.
        """
        return user.role