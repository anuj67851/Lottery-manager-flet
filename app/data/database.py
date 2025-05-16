from typing import Any, Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

from app.core.models import Base
from app.config import SQLALCHEMY_DATABASE_URL, DB_BASE_DIR # Import from config

# Ensure the database directory exists
DB_BASE_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    # echo=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    print(f"Initializing database at: {SQLALCHEMY_DATABASE_URL}")
    Base.metadata.create_all(bind=engine, checkfirst=True)
    print("Database tables checked/created.")

@contextmanager
def get_db_session() -> Generator[Session, Any, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()