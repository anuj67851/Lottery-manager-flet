from typing import Optional, List, Type
from sqlalchemy.orm import Session

from app.core.models import User # Explicit import of User model
from app.core.exceptions import UserNotFoundError, ValidationError, DatabaseError # Added DatabaseError
from app.data import crud_users
from app.constants import EMPLOYEE_ROLE, ALL_USER_ROLES # ALL_USER_ROLES for validation

class UserService:
    def get_user_by_id(self, db: Session, user_id: int) -> User: # Return User, raise if not found
        user = crud_users.get_user_by_id(db, user_id)
        if not user:
            raise UserNotFoundError(f"User with ID {user_id} not found.")
        return user

    def get_user_by_username(self, db: Session, username: str) -> User: # Return User, raise if not found
        user = crud_users.get_user_by_username(db, username)
        if not user:
            raise UserNotFoundError(f"User with username '{username}' not found.")
        return user

    def get_users_by_roles(self, db: Session, roles: List[str]) -> List[User]:
        # Validate roles if necessary
        for role in roles:
            if role not in ALL_USER_ROLES:
                raise ValidationError(f"Invalid role specified: {role}")
        return crud_users.get_users_by_roles(db, roles)

    def get_all_users(self, db: Session) -> List[User]:
        return crud_users.get_all_users(db)

    def any_users_exist(self, db: Session) -> bool: # Renamed from check_users_exist
        return crud_users.any_users_exist(db)

    def create_user(self, db: Session, username: str, password: str, role: str = EMPLOYEE_ROLE) -> User:
        if not username or not username.strip():
            raise ValidationError("Username cannot be empty.")
        if not password: # Add password complexity rules here if needed (e.g., length)
            raise ValidationError("Password cannot be empty.")
        if len(password) < 6: # Example rule
            raise ValidationError("Password must be at least 6 characters long.")
        if role not in ALL_USER_ROLES:
            raise ValidationError(f"Invalid user role: {role}.")
        # crud_users.create_user handles DatabaseError if username exists
        return crud_users.create_user(db, username.strip(), password, role)

    def update_user(self, db: Session, user_id: int, username: Optional[str] = None,
                    password: Optional[str] = None, role: Optional[str] = None, is_active: Optional[bool] = None) -> User:
        # Fetch user first to ensure it exists
        user_to_update = self.get_user_by_id(db, user_id) # This will raise UserNotFoundError if not found

        if username is not None and not username.strip():
            raise ValidationError("Username cannot be empty if provided for update.")
        if password is not None and not password: # If password is provided, it cannot be empty string
            raise ValidationError("New password cannot be empty.")
        if password is not None and len(password) < 6: # Example rule
            raise ValidationError("New password must be at least 6 characters long.")
        if role is not None and role not in ALL_USER_ROLES:
            raise ValidationError(f"Invalid user role for update: {role}.")

        # The CRUD operation will handle checking for username uniqueness if username is changed.
        return crud_users.update_user(db, user_id, username.strip() if username else None, password, role, is_active)

    def delete_user(self, db: Session, user_id: int) -> bool:
        # Ensure user exists before attempting delete
        user_to_delete = self.get_user_by_id(db, user_id) # Raises UserNotFoundError
        # Add any business logic checks here, e.g., cannot delete last admin user.
        return crud_users.delete_user(db, user_id)

    def deactivate_user(self, db: Session, user_id: int) -> User:
        user = self.get_user_by_id(db, user_id) # Ensures user exists
        if not user.is_active:
            # print(f"User {user_id} is already inactive.")
            return user # Or raise an error if trying to deactivate an already inactive user
        return crud_users.update_user(db, user_id, is_active=False)

    def reactivate_user(self, db: Session, user_id: int) -> User:
        user = self.get_user_by_id(db, user_id) # Ensures user exists
        if user.is_active:
            # print(f"User {user_id} is already active.")
            return user # Or raise an error
        return crud_users.update_user(db, user_id, is_active=True)