class AppException(Exception):
    """Base exception class for the application."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

class AuthenticationError(AppException):
    """Raised for authentication failures (e.g., invalid credentials, user not found for login)."""
    pass

class UserNotFoundError(AppException):
    """Raised when a specific user is expected but not found (e.g., when updating/deleting by ID)."""
    pass

class ValidationError(AppException):
    """Raised for data validation errors (e.g., missing fields, invalid format)."""
    pass

class DatabaseError(AppException):
    """Raised for errors during database operations (e.g., integrity constraints, connection issues)."""
    pass