from sqlalchemy.orm import Session

from app.data.crud_users import get_user_by_username
from app.core.models import User
from app.core.exceptions import AuthenticationError, ValidationError # Import custom exceptions

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
            AuthenticationError: If authentication fails (invalid username/password or user not found).
        """
        if not username:
            raise ValidationError("Username is required")

        if not password:
            raise ValidationError("Password is required")

        user = get_user_by_username(db, username)

        if not user:
            # For login, "Invalid username or password" is better than "User not found"
            # to avoid username enumeration.
            raise AuthenticationError("Invalid username or password")

        if not user.check_password(password):
            raise AuthenticationError("Invalid username or password")

        return user # Return user object directly

    @staticmethod
    def get_user_role(user: User) -> str:
        return user.role