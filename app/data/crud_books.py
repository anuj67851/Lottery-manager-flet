from typing import List, Optional, Dict, Any

from sqlalchemy import select, distinct
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload


from app.core.models import Book, SalesEntry, Game
from app.core.exceptions import DatabaseError, ValidationError, BookNotFoundError  # Assuming you might need these
from app.constants import REVERSE_TICKET_ORDER

def get_book_by_id(db: Session, book_id: int) -> Optional[Book]:
    return db.query(Book).options(joinedload(Book.game)).filter(Book.id == book_id).first()

def get_book_by_game_and_book_number(db: Session, game_id: int, book_number_str: str) -> Optional[Book]:
    return db.query(Book).filter(Book.game_id == game_id, Book.book_number == book_number_str).first()

def get_all_books_with_game_info(db: Session) -> List[Book]:
    """Fetches all books and eagerly loads their associated game information."""
    return db.query(Book).options(joinedload(Book.game)).order_by(Book.game_id, Book.book_number).all()

def create_book(db: Session, game: Game, book_number_str: str) -> Book:
    """
    Creates a new Book instance.
    Assumes game object is provided and valid.
    """
    if not game:
        raise ValueError("Game object must be provided to create a book.")
    if not book_number_str or len(book_number_str) != 7: # Basic validation
        raise ValidationError("Book number must be a 7-digit string.")

    # Check for duplicates before creating
    existing_book = get_book_by_game_and_book_number(db, game.id, book_number_str)
    if existing_book:
        raise DatabaseError(f"Book number '{book_number_str}' already exists for game ID '{game.id}'.")

    # Determine ticket_order and current_ticket_number based on the game
    ticket_order = game.default_ticket_order
    current_ticket_number = 0
    if ticket_order == REVERSE_TICKET_ORDER:
        current_ticket_number = game.total_tickets

    new_book = Book(
        game_id=game.id,
        book_number=book_number_str,
        ticket_order=ticket_order,
        current_ticket_number=current_ticket_number,
        is_active=False, # Books are inactive by default
        activate_date=None,
        game=game # Associate the game object directly
    )
    try:
        db.add(new_book)
        # db.commit() # Let the service layer or context manager handle commit
        # db.refresh(new_book) # Refresh might also be handled by service/context
        return new_book
    except IntegrityError as e:
        # db.rollback() # Handled by context manager
        # This could be due to the UniqueConstraint _game_id_book_number_uc
        raise DatabaseError(f"Could not create book. A book with number '{book_number_str}' might already exist for this game. Details: {e.orig}")
    except Exception as e:
        # db.rollback()
        raise DatabaseError(f"An unexpected error occurred while creating book: {e}")


def update_book_details(db: Session, book: Book, updates: Dict[str, Any]) -> Book:
    """
    Updates a book record with the provided dictionary of changes.
    """
    for key, value in updates.items():
        if hasattr(book, key):
            setattr(book, key, value)
        else:
            print(f"Warning: Attribute {key} not found on Book model during update.")
    try:
        return book
    except Exception as e:
        raise DatabaseError(f"Could not update book details: {e}")


def has_book_any_sales(db: Session, book_id: int) -> bool:
    """Checks if a specific book has any sales entries."""
    return db.query(SalesEntry.id).filter(SalesEntry.book_id == book_id).first() is not None

def delete_book_by_id(db: Session, book_id: int) -> bool:
    """Deletes a book by its ID."""
    book = get_book_by_id(db, book_id)
    if not book:
        raise BookNotFoundError(f"Book with ID {book_id} not found for deletion.")
    try:
        db.delete(book)
        # db.commit() # Commit handled by service layer or context manager
        return True
    except Exception as e:
        # db.rollback() # Handled by context manager
        raise DatabaseError(f"Could not delete book with ID {book_id}: {e}")

def get_book_ids_with_sales(db: Session) -> set[int]:
    """Returns a set of book IDs that have at least one sales entry."""
    stmt = select(distinct(SalesEntry.book_id))
    result = db.execute(stmt).scalars().all()
    return set(result)