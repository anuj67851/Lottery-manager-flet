from contextlib import contextmanager
from typing import Any, Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import SQLALCHEMY_DATABASE_URL, DB_BASE_DIR, SALES_PERSON_USERNAME, SALES_PERSON_PASSWORD, VERSION
from app.constants import SALESPERSON_ROLE, ADMIN_ROLE
# Import all models, including the new ShiftSubmission
from app.core.models import Base  # Added ShiftSubmission
from app.services import UserService, ConfigurationService

# Ensure the database directory exists
DB_BASE_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

@contextmanager
def get_db_session() -> Generator[Session, Any, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    print(f"Initializing database at: {SQLALCHEMY_DATABASE_URL}")
    # Base.metadata.create_all will now also create the 'shifts' table
    # because ShiftSubmission is imported and inherits from Base.
    Base.metadata.create_all(bind=engine, checkfirst=True)
    print("Database tables checked/created (including 'shifts' if new).")
    try:
        with get_db_session() as db:
            run_initialization_script(db)
            print("Initialization script completed.")
    except Exception as e:
        print(f"Error during database initialization script: {e}")
        raise


def run_initialization_script(db: Session):
    config_service = ConfigurationService()
    users_service = UserService()

    if not users_service.any_users_exist(db):
        print("Running for first time. Populating Sales User Info...")
        users_service.create_user(db, SALES_PERSON_USERNAME, SALES_PERSON_PASSWORD, SALESPERSON_ROLE)
        print("Sales User Info populated.")
        users_service.create_user(db, "admin", SALES_PERSON_PASSWORD, ADMIN_ROLE)
        print("Default admin user created.")

    if not config_service.get_license(db):
        print("Creating initial license record (active for dev)...")
        config_service.create_license_if_not_exists(db, license_is_active=True)
        print("Initial license record created.")

    version_record = config_service.get_version(db) # Renamed 'version' to 'version_record'
    if not version_record:
        print("Creating version record...")
        config_service.create_version(db)
        print("Version record created.")
    else:
        current_db_version_str = version_record.get_value()
        try:
            current_db_version = float(current_db_version_str)
            print(f"Version record already exists. Current DB version: {current_db_version}")
            # Migration logic (if VERSION from config.py is higher)
            if float(VERSION) > current_db_version:
                print(f"Need to perform migration from {current_db_version} to {VERSION}. Running migration script...")
                # Call your migration script/logic here if needed
                # For now, just updating the version in DB as an example
                # version_record.set_value(VERSION) # This should be part of a migration service
                # db.commit() # If migration service doesn't handle its own commit
                print(f"Placeholder: Version updated in DB to {VERSION}. Implement actual migration if schema changed beyond new tables.")
        except ValueError:
            print(f"Error: Could not parse database version '{current_db_version_str}' as float. Skipping migration check.")