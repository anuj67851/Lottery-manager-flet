from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import datetime

from app.core.models import Book, Game
from app.core.exceptions import DatabaseError, ValidationError, BookNotFoundError
from app.data import crud_books, crud_games
from app.constants import REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER

class BookService:
    def get_all_books_with_details(self, db: Session) -> List[Book]:
        return crud_books.get_all_books_with_game_info(db)

    def get_book_by_id(self, db: Session, book_id: int) -> Book:
        book = crud_books.get_book_by_id(db, book_id)
        if not book:
            raise BookNotFoundError(f"Book with ID {book_id} not found.")
        return book

    def activate_book(self, db: Session, book_id: int) -> Book:
        book = self.get_book_by_id(db, book_id)
        if book.is_active:
            # Or raise ValidationError("Book is already active.")
            return book

            # Ensure the game is not expired before activating a book
        if not book.game: # Should always have a game due to FK constraint
            raise DatabaseError(f"Book ID {book.id} is missing associated game data.")
        if book.game.is_expired:
            raise ValidationError(f"Cannot activate book for an expired game ('{book.game.name}').")

        book.is_active = True
        book.activate_date = datetime.datetime.now()
        book.finish_date = None # Clear finish date if it was previously set

        # crud_books.update_book_details(db, book, {"is_active": True, "activate_date": book.activate_date, "finish_date": None})
        # The commit will be handled by the get_db_session context manager
        return book


    def deactivate_book(self, db: Session, book_id: int) -> Book:
        book = self.get_book_by_id(db, book_id)
        if not book.is_active:
            # Or raise ValidationError("Book is already inactive.")
            return book
        book.is_active = False
        book.finish_date = datetime.datetime.now()
        # crud_books.update_book_details(db, book, {"is_active": False, "finish_date": book.finish_date})
        return book

    def edit_book(self, db: Session, book_id: int, new_book_number_str: Optional[str] = None, new_ticket_order: Optional[str] = None) -> Book:
        book = self.get_book_by_id(db, book_id)
        updates: Dict[str, Any] = {}

        if new_book_number_str is not None:
            if not (new_book_number_str.isdigit() and len(new_book_number_str) == 7):
                raise ValidationError("New book number must be a 7-digit string of numbers.")
            if new_book_number_str != book.book_number:
                # Check for duplicates with the new number for the same game
                existing_with_new_num = crud_books.get_book_by_game_and_book_number(db, book.game_id, new_book_number_str)
                if existing_with_new_num and existing_with_new_num.id != book_id:
                    raise DatabaseError(f"Book number '{new_book_number_str}' already exists for this game.")
                updates["book_number"] = new_book_number_str

        if new_ticket_order is not None and new_ticket_order in [REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER]:
            if new_ticket_order != book.ticket_order:
                if crud_books.has_book_any_sales(db, book_id):
                    raise ValidationError("Ticket order cannot be changed for books with sales entries.")
                updates["ticket_order"] = new_ticket_order
                # If ticket order changes, current_ticket_number must be reset
                if not book.game: # Should not happen
                    raise DatabaseError("Book is missing game association, cannot reset ticket number.")
                if new_ticket_order == REVERSE_TICKET_ORDER:
                    updates["current_ticket_number"] = book.game.total_tickets
                else:
                    updates["current_ticket_number"] = 0

        if not updates:
            return book # No changes

        return crud_books.update_book_details(db, book, updates)

    def add_books_in_batch(self, db: Session, books_data: List[Dict[str, Any]]) -> tuple[List[Book], List[str]]: # Ensure game_id is passed or fetched
        """
        Adds multiple books in a batch.
        Each dict in books_data should contain 'game_id' and 'book_number_str'.
        Returns a tuple: (list_of_successfully_created_book_objects, list_of_error_messages_for_failed_books).
        """
        created_books_list: List[Book] = []
        errors_list: List[str] = []

        # Game cache to avoid fetching the same game multiple times if books_data is sorted/grouped by game
        game_cache: Dict[int, Game] = {}

        for book_entry_data in books_data:
            game_id = book_entry_data.get("game_id") # Expecting game_id now
            book_number_str = book_entry_data.get("book_number_str")
            game_number_str = book_entry_data.get("game_number_str") # For error messages

            if game_id is None or not book_number_str: # game_id is crucial
                errors_list.append(f"Missing game_id or book_number for entry: {book_entry_data}")
                continue

            game = game_cache.get(game_id)
            if not game:
                game = crud_games.get_game_by_id(db, game_id) # Fetch by ID
                if not game:
                    errors_list.append(f"Game with ID '{game_id}' not found for book '{book_number_str}'.")
                    continue
                if game.is_expired:
                    errors_list.append(f"Game '{game.name}' (ID: {game_id}) is expired. Cannot add book '{book_number_str}'.")
                    continue
                game_cache[game_id] = game

            try:
                # crud_books.create_book expects the Game object and book_number_str
                new_book = crud_books.create_book(db, game, book_number_str)
                created_books_list.append(new_book)
            except (DatabaseError, ValidationError) as e:
                errors_list.append(f"Error adding book (GameNo:{game_number_str}, BookNo:{book_number_str}): {e.message if hasattr(e, 'message') else e}")
            except Exception as e_unhandled:
                errors_list.append(f"Unexpected error for book (GameNo:{game_number_str}, BookNo:{book_number_str}): {e_unhandled}")

        # No explicit commit here; relies on the get_db_session context manager.
        # If created_books_list is empty and errors_list is not, the calling code can decide to raise an exception.
        return created_books_list, errors_list # Always return two lists

    def has_book_any_sales(self, db: Session, book_id: int) -> bool:
        return crud_books.has_book_any_sales(db, book_id)


    def delete_book(self, db: Session, book_id: int) -> bool:
        """
        Deletes a book if it's not active and has no sales entries.
        """
        book_to_delete = self.get_book_by_id(db, book_id) # Raises BookNotFoundError if not found

        if book_to_delete.is_active:
            raise ValidationError("Cannot delete an active book. Deactivate it first.")

        if self.has_book_any_sales(db, book_id):
            raise ValidationError("Cannot delete a book with sales entries.")

        return crud_books.delete_book_by_id(db, book_id)

    def get_ids_of_books_with_sales(self, db: Session) -> set[int]:
        """Retrieves a set of all book IDs that have associated sales entries."""
        return crud_books.get_book_ids_with_sales(db)