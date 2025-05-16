from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import DatabaseError
from app.core.models import License


def create_license(db: Session):
    if get_license_status(db):
        raise DatabaseError(f"An active license already exists.")

    try:
        record = License()
        record.set_status(False)
        db.add(record)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DatabaseError(f"License already exists.")
    except Exception as e:
        db.rollback()
        raise DatabaseError(f"Could not create license: An unexpected error occurred.")

def get_license_status(db: Session) -> bool:
    license_record = db.query(License).first()
    return license_record is not None and license_record.is_active

def set_license_status(db, license_activated: bool):
    license_record = db.query(License).first()
    license_record.set_status(license_activated)