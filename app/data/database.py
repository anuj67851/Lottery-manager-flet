"""
Database connection and session management for the application.

This module provides functions to initialize the database, create tables,
and manage database sessions.
"""
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

# Assuming your models are in 'app.core.models' relative to your project root
# If this script is not at the project root, you might need to adjust sys.path
# or use relative imports carefully. For this example, let's assume 'app' is
# a top-level package.
from app.core.models import Base # Make sure Base is imported from where all your models are declared

# --- Configuration ---
DB_FILENAME = "lottery_manager.db"
DB_DIRECTORY = Path("./db")  # Store DB in a 'db' subdirectory relative to this script or project root
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_DIRECTORY.joinpath(DB_FILENAME)}"

# Ensure the database directory exists
DB_DIRECTORY.mkdir(parents=True, exist_ok=True)

# Create SQLite engine
# connect_args={"check_same_thread": False} is needed for SQLite when used
# in a multithreaded context (like Flet or some web servers) as SQLite
# by default only allows access from the thread that created the connection.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    # echo=True # Uncomment for debugging SQL queries
)

# Create sessionmaker
# autocommit=False: You manually commit transactions.
# autoflush=False: Data isn't automatically sent to the DB before a query;
#                  you control when to flush.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """
    Initialize the database.
    This function creates all tables defined in SQLAlchemy models
    (subclasses of Base) if they don't already exist.
    It's idempotent, meaning it's safe to call multiple times.
    """
    print(f"Initializing database at: {SQLALCHEMY_DATABASE_URL}")
    # Base.metadata.create_all will issue "CREATE TABLE IF NOT EXISTS"
    # or similar, so it's safe to call even if tables exist.
    # The `checkfirst=True` is an extra explicit check, often redundant with
    # modern SQLAlchemy and DBs but doesn't hurt.
    Base.metadata.create_all(bind=engine, checkfirst=True)
    print("Database tables checked/created.")

@contextmanager
def get_db_session() -> Session:
    """
    Provide a transactional scope around a series of operations.
    This function should be used with a 'with' statement to ensure
    the session is always closed.

    Usage:
        with get_db_session() as db:
            # do something with db
            db.commit() # if successful
    """
    db = SessionLocal()
    try:
        yield db  # Provide the session to the 'with' block
    except Exception:
        db.rollback()  # Rollback in case of an exception within the 'with' block
        raise          # Re-raise the exception
    finally:
        db.close()     # Always close the session