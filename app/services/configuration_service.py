from sqlalchemy.orm import Session

from app.config import LICENSE_CONFIG, VERSION, VERSION_CONFIG
from app.data import crud_configurations
from app.core.models import Configuration
from app.core.exceptions import DatabaseError


class ConfigurationService:
    def create_license_if_not_exists(self, db: Session, license_is_active: bool = False) -> Configuration:
        """Creates a license record if one doesn't already exist. Returns the existing or new license."""
        existing_license = crud_configurations.crud_get_license(db)
        if existing_license:
            return existing_license
        try:
            return crud_configurations.crud_create_configuration(db, name=LICENSE_CONFIG, value=str(license_is_active))
        except DatabaseError as e:
            existing_license = crud_configurations.crud_get_license(db)
            if existing_license:
                return existing_license
            raise e

    def get_license(self, db: Session) -> Configuration | None:
        """Retrieves the license record."""
        return crud_configurations.crud_get_license(db)

    def get_license_status(self, db: Session) -> bool:
        """Gets the current status of the license. Returns False if no license exists."""
        license = crud_configurations.crud_get_license(db)
        if license.get_value() == "False":
            return False
        else:
            return True
    def set_license_status(self, db: Session, license_activated: bool) -> Configuration:
        """Sets the license status. Creates a license if none exists, then sets its status."""
        license_record = crud_configurations.crud_get_license(db)
        if not license_record:
            license_record = self.create_license_if_not_exists(db, license_is_active=license_activated)

        # Ensure the status is what's requested, even if it was just created or already existed.
        if license_record.get_value() != str(license_activated):
            updated_license = crud_configurations.crud_set_license_status(db, str(license_activated))
            if not updated_license: # Should not happen if logic is correct
                raise DatabaseError("Failed to set license status after ensuring license exists.")
            return updated_license
        return license_record

    def get_version(self, db) -> Configuration | None:
        return crud_configurations.crud_get_version(db)

    def create_version(self, db):
        return crud_configurations.crud_create_configuration(db, name=VERSION_CONFIG, value=VERSION)