from contextlib import contextmanager
from typing import Any, Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import SQLALCHEMY_DATABASE_URL, VERSION, LICENSE_FILE_PATH
from app.core.models import Base
from app.services import UserService, ConfigurationService

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
    # DB_BASE_DIR is already created by main.py at this point
    print(f"Initializing database at: {SQLALCHEMY_DATABASE_URL}")
    Base.metadata.create_all(bind=engine, checkfirst=True)
    print("Database tables checked/created.")

    config_service = ConfigurationService()
    config_service.ensure_license_file_exists(default_active_status=False)
    print(f"License file checked/created at: {LICENSE_FILE_PATH}")

    try:
        with get_db_session() as db:
            run_initialization_script(db, config_service)
        print("Initialization script completed.")
    except Exception as e:
        print(f"Error during database initialization script: {e}")
        raise

def run_initialization_script(db: Session, config_service: ConfigurationService):
    users_service = UserService()

    if not users_service.any_users_exist(db):
        print("Running for first time. No users found in the database.")
        print("User setup (Salesperson) will need to be performed through the application interface on first launch.")

    version_record = config_service.get_version(db)
    if not version_record:
        print("Creating version record in DB...")
        config_service.create_version(db)
        print("Version record created.")
    else:
        current_db_version_str = version_record.get_value()
        try:
            current_db_version = float(current_db_version_str)
            print(f"Version record already exists. Current DB version: {current_db_version}")
            if float(VERSION) > current_db_version:
                print(f"Need to perform migration from {current_db_version} to {VERSION}. Placeholder for migration.")
        except ValueError:
            print(f"Error: Could not parse database version '{current_db_version_str}' as float. Skipping migration check.")