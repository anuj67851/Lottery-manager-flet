import logging
from typing import Optional, List, Type
from sqlalchemy.orm import Session
import re # For regex-based validation

from app.core.models import User
from app.core.exceptions import UserNotFoundError, ValidationError, DatabaseError
from app.data import crud_users
from app.constants import EMPLOYEE_ROLE, ALL_USER_ROLES, SALESPERSON_ROLE # Added SALESPERSON_ROLE for specific checks

logger = logging.getLogger("lottery_manager_app")
# Username validation constants
MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 30
# Regex for allowed username characters: alphanumeric and underscore, no spaces.
# Starts and ends with an alphanumeric character.
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*[a-zA-Z0-9]$")

# Password validation constants
MIN_PASSWORD_LENGTH = 6


class UserService:
    def _validate_username(self, username: str):
        if not username:
            raise ValidationError("Username cannot be empty.")
        if not (MIN_USERNAME_LENGTH <= len(username) <= MAX_USERNAME_LENGTH):
            raise ValidationError(f"Username must be between {MIN_USERNAME_LENGTH} and {MAX_USERNAME_LENGTH} characters long.")
        if not USERNAME_REGEX.match(username):
            raise ValidationError("Username can only contain letters, numbers, underscores, hyphens, or periods, and must start/end with a letter or number.")

    def _validate_password(self, password: str):
        if not password:
            raise ValidationError("Password cannot be empty.")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValidationError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")
        # if not PASSWORD_REGEX.match(password): # If using complex regex
        #     raise ValidationError("Password does not meet complexity requirements (e.g., uppercase, lowercase, number, special character).")

    def _validate_role(self, role: str, for_update: bool = False, existing_user_role: Optional[str] = None, user_being_edited_id: Optional[int]=None, current_acting_user_id: Optional[int]=None):
        if not role:
            raise ValidationError("Role cannot be empty.")
        if role not in ALL_USER_ROLES:
            raise ValidationError(f"Invalid user role: '{role}'. Valid roles are: {', '.join(ALL_USER_ROLES)}.")

        # Specific rule: Salesperson role cannot be assigned or changed to via general user update by another salesperson.
        # This role is special and typically set at creation or by specific logic.
        if for_update:
            if existing_user_role == SALESPERSON_ROLE and role != SALESPERSON_ROLE:
                raise ValidationError("The Salesperson role cannot be changed for an existing Salesperson user.")
            if role == SALESPERSON_ROLE and existing_user_role != SALESPERSON_ROLE:
                raise ValidationError("Cannot change role to Salesperson via this update method.")
            # Prevent an admin from demoting themselves if they are the only admin left (more complex, out of scope for now)
            # Prevent an admin from changing their own role if they are the one being edited
            if user_being_edited_id == current_acting_user_id and existing_user_role == "admin" and role != "admin":
                raise ValidationError("Administrators cannot change their own role.")


    def get_user_by_id(self, db: Session, user_id: int) -> User:
        user = crud_users.get_user_by_id(db, user_id)
        if not user:
            raise UserNotFoundError(f"User with ID {user_id} not found.")
        return user

    def get_user_by_username(self, db: Session, username: str) -> User:
        self._validate_username(username) # Validate even for reads if format is important for lookup
        user = crud_users.get_user_by_username(db, username)
        if not user:
            raise UserNotFoundError(f"User with username '{username}' not found.")
        return user

    def get_users_by_roles(self, db: Session, roles: List[str]) -> List[User]:
        for role in roles:
            self._validate_role(role) # Validates if each role in the list is a known role
        return crud_users.get_users_by_roles(db, roles)

    def get_all_users(self, db: Session) -> List[User]:
        return crud_users.get_all_users(db)

    def any_users_exist(self, db: Session) -> bool:
        return crud_users.any_users_exist(db)

    def create_user(self, db: Session, username: str, password: str, role: str = EMPLOYEE_ROLE) -> User:
        username = username.strip() # Clean username first
        self._validate_username(username)
        self._validate_password(password)
        self._validate_role(role)

        # crud_users.create_user handles DatabaseError if username (unique constraint) exists
        try:
            logger.info(f"Attempting to create new user '{username}' with role '{role}'.")
            return crud_users.create_user(db, username, password, role)
        except DatabaseError as e: # Re-raise specific DB errors
            raise e
        except Exception as e_unhandled: # Catch other unexpected issues from CRUD
            raise DatabaseError(f"An unexpected error occurred while creating user in database: {e_unhandled}")


    def update_user(self, db: Session, user_id: int, username: Optional[str] = None,
                    password: Optional[str] = None, role: Optional[str] = None,
                    is_active: Optional[bool] = None, current_acting_user_id: Optional[int] = None) -> User:
        user_to_update = self.get_user_by_id(db, user_id) # Raises UserNotFoundError if not found

        if username is not None:
            username = username.strip()
            self._validate_username(username)
        if password is not None: # Password can be empty string if intent is to clear, but our validation prevents it
            if not password: # If explicitly an empty string is passed to clear, it's usually bad.
                raise ValidationError("New password cannot be empty if you intend to change it. Omit to keep unchanged.")
            self._validate_password(password)
        if role is not None:
            self._validate_role(role, for_update=True, existing_user_role=user_to_update.role, user_being_edited_id=user_id, current_acting_user_id=current_acting_user_id)


        # The CRUD operation will handle checking for username uniqueness if username is changed.
        try:
            logger.info(f"Attempting to update user ID {user_id}. Changes: username='{username}', role='{role}', is_active='{is_active}'. Password change attempted: {'Yes' if password else 'No'}.")
            return crud_users.update_user(db, user_id, username, password, role, is_active)
        except DatabaseError as e: # Re-raise specific DB errors
            raise e
        except Exception as e_unhandled: # Catch other unexpected issues from CRUD
            raise DatabaseError(f"An unexpected error occurred while updating user in database: {e_unhandled}")


    def delete_user(self, db: Session, user_id: int) -> bool:
        # Ensure user exists before attempting delete
        user_to_delete = self.get_user_by_id(db, user_id)
        # Add business logic: e.g., cannot delete the only Salesperson or Admin.
        # For simplicity, this check is omitted here but important for production.
        if user_to_delete.role == SALESPERSON_ROLE:
            # Check if this is the last salesperson
            salespersons = self.get_users_by_roles(db, [SALESPERSON_ROLE])
            if len(salespersons) <= 1:
                logger.warning(f"Attempt to delete last salesperson account '{user_to_delete.username}' was blocked.")
                raise ValidationError("Cannot delete the last Salesperson account.")

        logger.info(f"Attempting to delete user '{user_to_delete.username}' (ID: {user_to_delete.id}).")
        return crud_users.delete_user(db, user_id)

    def deactivate_user(self, db: Session, user_id: int, current_acting_user_id: Optional[int] = None) -> User:
        user = self.get_user_by_id(db, user_id)
        if user.id == current_acting_user_id:
            raise ValidationError("Users cannot deactivate their own account.")
        if user.role == SALESPERSON_ROLE:
            raise ValidationError("Salesperson accounts cannot be deactivated through this method. Consider role change or deletion if necessary and appropriate.")
        if not user.is_active:
            return user # Already inactive
        logger.info(f"Deactivating user '{user.username}' (ID: {user.id}) by user ID {current_acting_user_id}.")
        return crud_users.update_user(db, user_id, is_active=False)

    def reactivate_user(self, db: Session, user_id: int) -> User:
        user = self.get_user_by_id(db, user_id)
        if user.role == SALESPERSON_ROLE:
            # Salespersons are typically always active if they exist.
            # If one was somehow made inactive, this allows reactivation.
            pass
        if user.is_active:
            return user # Already active
        logger.info(f"Reactivating user '{user.username}' (ID: {user.id}).")
        return crud_users.update_user(db, user_id, is_active=True)