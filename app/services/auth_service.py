from sqlalchemy.orm import Session

from app.data.crud_users import get_user_by_username # Direct DAO access for this specific need
from app.core.models import User
from app.core.exceptions import AuthenticationError, ValidationError

class AuthService:
    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> User:
        """
        Authenticate a user with username and password.

        Args:
            db (Session): The database session.
            username (str): The username to authenticate.
            password (str): The password to authenticate.

        Returns:
            User: The authenticated user.

        Raises:
            ValidationError: If username or password is not provided.
            AuthenticationError: If authentication fails (invalid username/password or user not found or inactive).
        """
        if not username:
            raise ValidationError("Username is required.") # Consistent error messages

        if not password:
            raise ValidationError("Password is required.") # Consistent error messages

        user = get_user_by_username(db, username)

        if not user:
            # Do not reveal if username exists or not for security.
            raise AuthenticationError("Invalid username or password.")

        if not user.check_password(password):
            raise AuthenticationError("Invalid username or password.")

        if not user.is_active:
            # User exists and password is correct, but account is inactive.
            raise AuthenticationError("User account is not active. Please contact an administrator.")

        return user

    @staticmethod
    def get_user_role(user: User) -> str:
        if not user or not hasattr(user, 'role'):
            raise ValueError("Invalid user object provided.")
        return user.role