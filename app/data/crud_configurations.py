from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import LICENSE_CONFIG, VERSION_CONFIG
from app.core.models import Configuration
from app.core.exceptions import DatabaseError


def crud_create_configuration(db: Session, name: str = "", value: str = "") -> Configuration:
    """
    Creates a new configuration.
    Raises DatabaseError if a configuration already exists or on other DB issues.
    """
    if db.query().filter(Configuration.name == name).first():
        return db.query().filter(Configuration.name == name).first()

    try:
        new_config = Configuration(name=name, value=value)
        db.add(new_config)
        db.commit()
        db.refresh(new_config)
        return new_config
    except IntegrityError:
        db.rollback()
        raise DatabaseError(f"Config {name} creation failed due to a conflict (e.g. already exists).")
    except Exception as e:
        db.rollback()
        raise DatabaseError(f"Could not create configuration {name}: An unexpected error occurred: {e}")


def crud_get_license(db: Session) -> Configuration | None:
    """Retrieves the first license record."""
    return db.query(Configuration).filter(Configuration.name == LICENSE_CONFIG).first()

def crud_get_version(db: Session) -> Configuration | None:
    """Retrieves the first version record."""
    return db.query(Configuration).filter(Configuration.name == VERSION_CONFIG).first()


def crud_set_license_status(db: Session, license_activated: str = "False") -> Configuration | None:
    """Sets the active status of the first license record. Creates one if none exists."""
    license_record = db.query(Configuration).filter(Configuration.name == LICENSE_CONFIG).first()

    if not license_record:
        try:
            license_record = Configuration(name=LICENSE_CONFIG, value=license_activated) # Create with the desired status
            db.add(license_record)
        except Exception as e:
            db.rollback()
            raise DatabaseError(f"Could not create new license during update: {e}")
    else:
        license_record.set_value(license_activated)

    try:
        db.commit()
        if license_record:
            db.refresh(license_record)
        return license_record
    except Exception as e:
        db.rollback()
        raise DatabaseError(f"Could not update license status: An unexpected error occurred: {e}")