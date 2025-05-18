import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.models import SalesEntry
from app.core.exceptions import DatabaseError

def create_sales_entry(db: Session, sales_entry_data: SalesEntry) -> SalesEntry:
    """
    Adds a pre-configured SalesEntry object to the database.
    Assumes sales_entry_data.calculate_count_and_price() has been called.
    """
    try:
        db.add(sales_entry_data)
        # The commit will be handled by the service layer's context manager (get_db_session)
        # We might need to flush to ensure the object is persisted if other operations
        # in the same session depend on this SalesEntry immediately.
        # For now, assume service layer handles commit appropriately.
        return sales_entry_data
    except IntegrityError as e:
        # db.rollback() # Handled by context manager
        raise DatabaseError(f"Could not create sales entry due to an integrity constraint: {e.orig}")
    except Exception as e:
        # db.rollback() # Handled by context manager
        raise DatabaseError(f"Could not create sales entry: An unexpected error occurred: {e}")

def get_sales_entry_by_id(db: Session, sales_entry_id: int) -> SalesEntry | None:
    return db.query(SalesEntry).filter(SalesEntry.id == sales_entry_id).first()

def get_sales_entries_for_book(db: Session, book_id: int) -> list[SalesEntry]:
    return db.query(SalesEntry).filter(SalesEntry.book_id == book_id).order_by(SalesEntry.date.desc()).all()

def get_sales_entries_by_date_range(db: Session, start_date: datetime.datetime, end_date: datetime.datetime) -> list[SalesEntry]:
    return db.query(SalesEntry).filter(SalesEntry.date >= start_date, SalesEntry.date <= end_date).order_by(SalesEntry.date.desc()).all()