from sqlalchemy.orm import Session
from app.data import crud_license
from app.core.models import License
from app.core.exceptions import DatabaseError # Added DatabaseError


class LicenseService:
    def create_license_if_not_exists(self, db: Session, license_is_active: bool = False) -> License: # Renamed
        """Creates a license record if one doesn't already exist. Returns the existing or new license."""
        existing_license = crud_license.crud_get_license(db)
        if existing_license:
            return existing_license
        # crud_create_license in the original might return existing one,
        # but better to be explicit here.
        try:
            # If crud_create_license is changed to strictly create, this is fine.
            # If it can return existing, the check above is redundant.
            # Assuming crud_create_license will create if none exists.
            return crud_license.crud_create_license(db, license_is_active=license_is_active)
        except DatabaseError as e: # Catch if creation fails specifically
            # This might happen if crud_create_license fails due to a race condition
            # where another transaction created it. Try fetching again.
            existing_license = crud_license.crud_get_license(db)
            if existing_license:
                return existing_license
            raise e # Re-raise original DatabaseError if still not found

    def get_license(self, db: Session) -> License | None:
        """Retrieves the license record."""
        return crud_license.crud_get_license(db)

    def get_license_status(self, db: Session) -> bool:
        """Gets the current status of the license. Returns False if no license exists."""
        return crud_license.crud_get_license_status(db)

    def set_license_status(self, db: Session, license_activated: bool) -> License:
        """Sets the license status. Creates a license if none exists, then sets its status."""
        license_record = crud_license.crud_get_license(db)
        if not license_record:
            # Create it with the desired initial status directly.
            # crud_create_license might not take initial status correctly if it "returns existing".
            # This ensures if we create, it's with the intended status.
            license_record = self.create_license_if_not_exists(db, license_is_active=license_activated)
            # If it was just created, its status is already set.
            # If an existing one was returned by create_license_if_not_exists, we might need to update.
            # So, always ensure status is set after getting/creating.

        # Ensure the status is what's requested, even if it was just created or already existed.
        if license_record.is_active != license_activated:
            updated_license = crud_license.crud_set_license_status(db, license_activated)
            if not updated_license: # Should not happen if logic is correct
                raise DatabaseError("Failed to set license status after ensuring license exists.")
            return updated_license
        return license_record