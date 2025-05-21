import logging
from contextlib import contextmanager
from typing import Any, Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import SQLALCHEMY_DATABASE_URL, VERSION, LICENSE_FILE_PATH
from app.core.models import Base
from app.services import UserService, ConfigurationService

logger = logging.getLogger(__name__)
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
    logger.info(f"Initializing database at: {SQLALCHEMY_DATABASE_URL}")
    Base.metadata.create_all(bind=engine, checkfirst=True)
    logger.info("Database tables checked/created.")

    config_service = ConfigurationService()
    config_service.ensure_license_file_exists(default_active_status=False)
    logger.info(f"License file checked/created at: {LICENSE_FILE_PATH}")

    try:
        with get_db_session() as db:
            run_initialization_script(db, config_service)
        logger.info("Initialization script completed.")
    except Exception as e:
        logger.info(f"Error during database initialization script: {e}")
        raise

def run_initialization_script(db: Session, config_service: ConfigurationService):
    users_service = UserService()

    if not users_service.any_users_exist(db):
        logger.info("Running for first time. No users found in the database.")
        logger.info("User setup (Salesperson) will need to be performed through the application interface on first launch.")

    version_record = config_service.get_version(db)
    if not version_record:
        logger.info("Creating version record in DB...")
        config_service.create_version(db)
        logger.info("Version record created.")
    else:
        current_db_version_str = version_record.get_value()
        try:
            current_db_version = float(current_db_version_str)
            logger.info(f"Version record already exists. Current DB version: {current_db_version}")
            if float(VERSION) > current_db_version:
                logger.info(f"Need to perform migration from {current_db_version} to {VERSION}. Placeholder for migration.")
        except ValueError as e:
            logger.error(f"Error: Could not parse database version '{current_db_version_str}' as float. Skipping migration check.", exc_info=e)