from typing import Optional, List, Type
from sqlalchemy.orm import Session

from app.data import crud_users
from app.core.models import User
from app.core.exceptions import ValidationError
from app.constants import EMPLOYEE_ROLE

class UserService:
    def get_user_by_id(self, db: Session, user_id: int) -> Optional[User]:
        return crud_users.get_user_by_id(db, user_id)

    def get_user_by_username(self, db: Session, username: str) -> Optional[User]:
        return crud_users.get_user_by_username(db, username)

    def get_users_by_roles(self, db: Session, roles: List[str]) -> List[Type[User]]:
        return crud_users.get_users_by_roles(db, roles)

    def get_all_users(self, db: Session) -> List[Type[User]]:
        return crud_users.get_all_users(db)

    def check_users_exist(self, db: Session) -> bool:
        return crud_users.any_users_exist(db)

    def create_user(self, db: Session, username: str, password: str, role: str = EMPLOYEE_ROLE) -> User:
        # Validation and business logic can be added here if more complex than CRUD
        if not username or not password or not role:
            raise ValidationError("Username, password, and role are required to create a user.")
        return crud_users.create_user(db, username, password, role)

    def update_user(self, db: Session, user_id: int, username: Optional[str] = None,
                    password: Optional[str] = None, role: Optional[str] = None) -> User:
        # More complex validation or checks can go here
        return crud_users.update_user(db, user_id, username, password, role)

    def delete_user(self, db: Session, user_id: int) -> bool:
        # Add any pre-delete checks or related actions here
        return crud_users.delete_user(db, user_id)

    def deactivate_user(self, db: Session, user_id: int):
        user = self.get_user_by_id(db, user_id)
        if not user:
            raise ValidationError(f"User with ID {user_id} not found.")
        user.is_active = False
        db.commit()

    def reactivate_user(self, db: Session, user_id: int):
        user = self.get_user_by_id(db, user_id)
        if not user:
            raise ValidationError(f"User with ID {user_id} not found.")
        user.is_active = True
        db.commit()

    def any_users_exist(self, db: Session) -> bool:
        return crud_users.any_users_exist(db)
