from sqlalchemy.orm import Session
from app.data import crud_license
from app.core.models import License

class LicenseService:
    def create_license_if_not_exists(self, db: Session, license: bool = False) -> License:
        """Creates a license record if one doesn't already exist."""
        existing_license = crud_license.crud_get_license(db)
        if existing_license:
            return existing_license
        return crud_license.crud_create_license(db, license=license)

    def get_license(self, db: Session) -> License | None:
        """Retrieves the license record."""
        return crud_license.crud_get_license(db)

    def get_license_status(self, db: Session) -> bool:
        """Gets the current status of the license."""
        return crud_license.crud_get_license_status(db)

    def set_license_status(self, db: Session, license_activated: bool) -> License | None:
        """Sets the license status. Creates a license if none exists."""
        # crud_set_license_status handles creation if necessary
        return crud_license.crud_set_license_status(db, license_activated)
