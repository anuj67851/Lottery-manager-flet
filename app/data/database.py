from typing import Any, Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

from app.constants import SALESPERSON_ROLE, ADMIN_ROLE
from app.core.models import Base
from app.config import SQLALCHEMY_DATABASE_URL, DB_BASE_DIR, SALES_PERSON_USERNAME, SALES_PERSON_PASSWORD
from app.services import UserService # Direct import for initialization
from app.services.license_service import LicenseService # Direct import


# Ensure the database directory exists
DB_BASE_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}, # Required for SQLite with Flet/FastAPI
)

# expire_on_commit=False is important for Flet so objects accessed after commit are still usable
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

@contextmanager
def get_db_session() -> Generator[Session, Any, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit() # Commit successful operations
    except Exception:
        db.rollback() # Rollback on any error
        raise # Re-raise the exception so it can be handled upstream
    finally:
        db.close()

def init_db():
    print(f"Initializing database at: {SQLALCHEMY_DATABASE_URL}")
    Base.metadata.create_all(bind=engine, checkfirst=True) # checkfirst is good practice
    print("Database tables checked/created.")
    try:
        with get_db_session() as db:
            run_initialization_script(db)
            print("Initialization script completed.")
    except Exception as e:
        print(f"Error during database initialization script: {e}")
        # Depending on the severity, you might want to exit or handle this
        raise


def run_initialization_script(db: Session):
    # TODO : FIX THIS IN FINAL PRODUCT (REMOVE ADMIN CREATION AND LICENSE TO FALSE, CHANGE SALES PASSWORD TOO)
    license_service = LicenseService()
    users_service = UserService()

    # Create Salesperson and Admin only if no users exist at all
    if not users_service.any_users_exist(db): # Changed from check_users_exist to any_users_exist
        print("Running for first time. Populating Sales User Info...")
        users_service.create_user(db, SALES_PERSON_USERNAME, SALES_PERSON_PASSWORD, SALESPERSON_ROLE)
        print("Sales User Info populated.")
        # Create a default admin user
        users_service.create_user(db, "admin", SALES_PERSON_PASSWORD, ADMIN_ROLE) # Using the same password for now
        print("Default admin user created.")

    # Ensure a license record exists, default to True (active) for development as per original
    if not license_service.get_license(db):
        print("Creating initial license record (active for dev)...")
        license_service.create_license_if_not_exists(db, license_is_active=True) # Set to True as per original behavior
        print("Initial license record created.")
    # else: # If license exists, ensure it's active for dev as per original logic
    #     if not license_service.get_license_status(db):
    #         print("Activating existing license for dev...")
    #         license_service.set_license_status(db, True)