from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.models import License
from app.core.exceptions import DatabaseError # Import custom exception


def crud_create_license(db: Session, license: bool = False) -> License:
    """
    Creates a new license record, defaulting to inactive.
    Raises DatabaseError if a license already exists or on other DB issues.
    """
    if db.query(License).first(): # Check if any license record exists
        return db.query(License).first() # Return existing if it's okay

    try:
        new_license = License(is_active=license)
        db.add(new_license)
        db.commit()
        db.refresh(new_license)
        return new_license
    except IntegrityError: # Should be caught by the pre-check, but as a fallback
        db.rollback()
        raise DatabaseError("License record creation failed due to a conflict (e.g. already exists).")
    except Exception as e:
        db.rollback()
        raise DatabaseError(f"Could not create license: An unexpected error occurred: {e}")


def crud_get_license(db: Session) -> License | None:
    """Retrieves the first license record."""
    return db.query(License).first()


def crud_get_license_status(db: Session) -> bool:
    """Retrieves the active status of the first license record."""
    license_record = db.query(License).first()
    return license_record.is_active if license_record else False


def crud_set_license_status(db: Session, license_activated: bool) -> License | None:
    """Sets the active status of the first license record. Creates one if none exists."""
    license_record = db.query(License).first()
    if not license_record:
        license_record = crud_create_license(db) # Ensure a license record exists
        # If crud_create_license raises an error, it will propagate.

    try:
        license_record.set_status(license_activated)
        db.commit()
        db.refresh(license_record)
        return license_record
    except Exception as e:
        db.rollback()
        raise DatabaseError(f"Could not update license status: An unexpected error occurred: {e}")
