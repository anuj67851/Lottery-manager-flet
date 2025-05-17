from typing import Any, Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

from app.constants import SALESPERSON_ROLE
from app.core.models import Base
from app.config import SQLALCHEMY_DATABASE_URL, DB_BASE_DIR, SALES_PERSON_USERNAME, SALES_PERSON_PASSWORD
from app.services import UserService
from app.services.license_service import LicenseService


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
        db.commit() # Commit successful operations
    except Exception:
        db.rollback() # Rollback on any error
        raise
    finally:
        db.close()

def init_db():
    print(f"Initializing database at: {SQLALCHEMY_DATABASE_URL}")
    Base.metadata.create_all(bind=engine, checkfirst=True)
    print("Database tables checked/created.")
    with get_db_session() as db:
        run_initialization_script(db)
        print("Initialization script completed.")


def run_initialization_script(db: Session):
    license_service = LicenseService()
    users_service = UserService()

    if not users_service.check_users_exist(db):
        print("Running for first time. Populating Sales User Info...")
        users_service.create_user(db, SALES_PERSON_USERNAME, SALES_PERSON_PASSWORD, SALESPERSON_ROLE)
        print("Sales User Info populated...")

    # Ensure a license record exists
    if not license_service.get_license(db):
        print("Creating initial license record (inactive)...")
        license_service.create_license_if_not_exists(db)
        print("Initial license record created.")

