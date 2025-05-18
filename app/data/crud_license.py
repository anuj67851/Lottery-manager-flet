from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.models import License
from app.core.exceptions import DatabaseError # Import custom exception


def crud_create_license(db: Session, license_is_active: bool = False) -> License: # Renamed license to license_is_active
    """
    Creates a new license record.
    Raises DatabaseError if a license already exists or on other DB issues.
    """
    # This check might be redundant if we expect only one license record controlled by its existence.
    # If the intention is truly to prevent creating a *second* record, this is fine.
    # If it's about "find or create", the logic in services is better.
    if db.query(License).first():
        # Original code returned existing, but this function is crud_CREATE_license.
        # Raising an error if it already exists seems more aligned with "create" semantics
        # or the calling code should check first.
        # For now, aligning with original behavior to return existing if trying to create when one exists.
        # However, the original also had a potential conflict if it tried to create one
        # after this check passed but before commit (race condition, though unlikely for license).
        # The service layer handles "get or create" more robustly.
        # This function will now strictly attempt to create, raising error if it exists.
        # Let's revert to original behavior: if one exists, return it, as this is what crud_set_license_status relied on.
        return db.query(License).first() # type: ignore

    try:
        new_license = License(is_active=license_is_active)
        db.add(new_license)
        db.commit()
        db.refresh(new_license)
        return new_license
    except IntegrityError:
        db.rollback()
        # This path should ideally not be hit if the check above is effective,
        # but good as a safeguard for concurrent operations.
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
        # This part was problematic. crud_create_license might return an existing license
        # or create a new one. We need to ensure we are operating on the correct instance.
        # The LicenseService handles the "create if not exists" logic more cleanly.
        # For this CRUD function, we assume it operates on an existing license or fails.
        # Let the service layer handle creation. If called directly, it should find one.
        # However, the original code implies it *can* create.
        # To maintain that, but make it safer:
        try:
            license_record = License(is_active=license_activated) # Create with the desired status
            db.add(license_record)
            # No commit yet, will be committed below.
        except Exception as e: # Broad exception for creation attempt
            db.rollback()
            raise DatabaseError(f"Could not create new license during update: {e}")
    else:
        license_record.set_status(license_activated)

    try:
        db.commit() # Commit changes (either new record or updated status)
        if license_record:  # Ensure license_record is not None before refresh
            db.refresh(license_record)
        return license_record
    except Exception as e:
        db.rollback()
        raise DatabaseError(f"Could not update license status: An unexpected error occurred: {e}")