from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import VERSION_CONFIG
from app.core.models import Configuration
from app.core.exceptions import DatabaseError


def crud_create_configuration(db: Session, name: str = "", value: str = "") -> Configuration:
    """
    Creates a new configuration in the database.
    Raises DatabaseError if a configuration already exists or on other DB issues.
    """
    # Check if it already exists (e.g., for version)
    existing_config = db.query(Configuration).filter(Configuration.name == name).first()
    if existing_config:
        return existing_config # Return existing if found (idempotency for simple cases)

    try:
        new_config = Configuration(name=name, value=value)
        db.add(new_config)
        # db.commit() # Commit will be handled by the service layer or session context
        # db.refresh(new_config)
        return new_config
    except IntegrityError:
        # db.rollback() # Handled by session context
        raise DatabaseError(f"Config {name} creation failed due to a conflict (e.g. already exists).")
    except Exception as e:
        # db.rollback() # Handled by session context
        raise DatabaseError(f"Could not create configuration {name}: An unexpected error occurred: {e}")

def crud_get_version(db: Session) -> Configuration | None:
    """Retrieves the first version record from the database."""
    return db.query(Configuration).filter(Configuration.name == VERSION_CONFIG).first()
