Okay, I've incorporated the requested changes. This involves creating a common scan input component, a generalized dialog for book actions, refactoring existing views to use these, implementing the "Full Book Sale" and "Activate Book" functionalities, and ensuring the "scanned row to top" behavior in the sales entry table.

Here are the files that have been modified or added, along with explanations:

**Summary of Key Changes & New Components:**

1.  **`app/ui/components/common/scan_input_handler.py` (New):**
    *   A reusable `ScanInputHandler` class. It's not a Flet `Control` itself but a helper class to manage scan input logic (parsing, validation, callbacks). Views will create a `ft.TextField` and pass it to this handler.
    *   This handler is used by `SalesEntryView`, and the new `BookActionDialog`.

2.  **`app/ui/components/dialogs/book_action_dialog.py` (New):**
    *   A generic dialog for actions involving selecting books via scan/manual entry.
    *   Used for "Add New Books", "Full Book Sale", and "Activate Book".
    *   Manages a temporary list of books, displays them in a table, and calls a batch processing callback on confirmation.

3.  **`app/ui/views/admin_dashboard_view.py`:**
    *   "Full Book Sale" and "Activate Book" buttons are now functional.
    *   They open the `BookActionDialog` with appropriate configurations.
    *   Modified `create_nav_card_button` to accept an `on_click_override` for dialogs.

4.  **`app/ui/components/tables/sales_entry_items_table.py`:**
    *   Implemented the "move scanned/updated row to top" functionality.

5.  **`app/ui/views/admin/sales_entry_view.py`:**
    *   Uses the `ScanInputHandler` for its scanner input field.

6.  **`app/ui/views/admin/book_management.py`:**
    *   The "Add New Books" dialog is now an instance of `BookActionDialog`.

7.  **`app/services/book_service.py` & `app/services/sales_entry_service.py`:**
    *   Added methods to support "Full Book Sale" (deactivating book, setting ticket numbers) and batch activation.
    *   `SalesEntryService` now has a method to create the specific sales entry for a full book sale.

8.  **`app/ui/components/widgets/function_button.py`:**
    *   `create_nav_card_button` updated to accept an `on_click_override` parameter.

**Documentation and modularity have been prime considerations throughout these changes.**

--- START OF CHANGED FILES ---

```python
// Filename: app/constants.py
ADMIN_ROLE = "admin"
EMPLOYEE_ROLE = "employee"
SALESPERSON_ROLE = "salesperson"

ALL_USER_ROLES = [ADMIN_ROLE, EMPLOYEE_ROLE, SALESPERSON_ROLE]
# Roles that can be typically managed (created/edited by an admin/salesperson)
MANAGED_USER_ROLES = [ADMIN_ROLE, EMPLOYEE_ROLE]

# QR code constants
QR_TOTAL_LENGTH = 29
GAME_LENGTH = 3
BOOK_LENGTH = 7
TICKET_LENGTH = 3
MIN_REQUIRED_SCAN_LENGTH = GAME_LENGTH + BOOK_LENGTH # Minimum for Game+Book
MIN_REQUIRED_SCAN_LENGTH_WITH_TICKET = GAME_LENGTH + BOOK_LENGTH + TICKET_LENGTH

# Ticket orders
REVERSE_TICKET_ORDER = "reverse"
FORWARD_TICKET_ORDER = "forward"

# Route Names
LOGIN_ROUTE = "login"
ADMIN_DASHBOARD_ROUTE = "admin_dashboard"
EMPLOYEE_DASHBOARD_ROUTE = "employee_dashboard"
SALESPERSON_DASHBOARD_ROUTE = "salesperson_dashboard"

# Game Management routes
GAME_MANAGEMENT_ROUTE = "game_management"

# Book management routes
BOOK_MANAGEMENT_ROUTE = "book_management"

# Sales Entry Route
SALES_ENTRY_ROUTE = "sales_entry"

# Book Action Dialog Types (used for configuration)
BOOK_ACTION_ADD_NEW = "add_new"
BOOK_ACTION_FULL_SALE = "full_sale"
BOOK_ACTION_ACTIVATE = "activate"

```
--- File Separator ---
```python
// Filename: app/core/models.py
"""
Defines the SQLAlchemy models for the application.

This module contains the database schema definitions using SQLAlchemy's
declarative base. It includes the `User`, `Game`, `Book`,
and `SalesEntry` models.
"""
import bcrypt
import datetime
from sqlalchemy import String, Integer, Column, ForeignKey, Boolean, DateTime, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from app.constants import REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER

Base = declarative_base()

class User(Base):
    """
    Represents a user in the system.

    Attributes:
        id (int): The primary key for the user.
        username (str): The unique username for the user.
        password (str): The hashed password for the user.
        role (str): The role of the user (e.g., "employee", "admin").
                    Defaults to "employee".
        created_date (DateTime): The date and time when the user was created.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="employee")
    created_date = Column(DateTime, nullable=False, default=datetime.datetime.now)
    is_active = Column(Boolean, nullable=False, default=True)

    def set_password(self, plain_password: str):
        password_bytes = plain_password.encode('utf-8')
        salt = bcrypt.gensalt()
        self.password = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

    def check_password(self, plain_password: str) -> bool:
        if not self.password:
            return False
        password_bytes = plain_password.encode('utf-8')
        hashed_password_bytes = self.password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_password_bytes)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"

class Game(Base):
    """
    Represents a game in the system.
    """
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False, unique=False)
    price = Column(Integer, nullable=False)
    total_tickets = Column(Integer, nullable=False)
    is_expired = Column(Boolean, nullable=False, default=False)
    default_ticket_order = Column(String, nullable=False, default=REVERSE_TICKET_ORDER)
    created_date = Column(DateTime, nullable=False, default=datetime.datetime.now)
    expired_date = Column(DateTime, nullable=True)

    books = relationship("Book", back_populates="game")
    game_number = Column(Integer, nullable=False, unique=True)

    @property
    def calculated_total_value(self) -> int:
        return (self.price * self.total_tickets) if self.price is not None and self.total_tickets is not None else 0

    def __repr__(self):
        return (f"<Game(id={self.id}, name='{self.name}', price={self.price}, total_tickets={self.total_tickets}, "
                f"game_number={self.game_number}, default_ticket_order='{self.default_ticket_order}', is_expired={self.is_expired})>")

class Book(Base):
    """
    Represents an instance of a book, often a specific print run or batch.
    """
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    book_number = Column(String(7), nullable=False) # Preserves leading zeros
    ticket_order = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)
    activate_date = Column(DateTime, nullable=True)
    finish_date = Column(DateTime, nullable=True)
    current_ticket_number = Column(Integer, nullable=False) # Initialized based on game and order

    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    game = relationship("Game", back_populates="books")
    sales_entries = relationship("SalesEntry", back_populates="book")
    __table_args__ = (UniqueConstraint('game_id', 'book_number', name='_game_id_book_number_uc'),)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.game:
            if 'ticket_order' not in kwargs or self.ticket_order is None:
                self.ticket_order = self.game.default_ticket_order

            if 'current_ticket_number' not in kwargs or self.current_ticket_number is None : # Ensure current_ticket_number is initialized
                self._initialize_current_ticket_number()
        elif 'current_ticket_number' not in kwargs or self.current_ticket_number is None: # Fallback if game not present during init
            self.current_ticket_number = 0


    def _initialize_current_ticket_number(self):
        """Sets the initial current_ticket_number based on game and ticket_order."""
        if self.game:
            if self.ticket_order == REVERSE_TICKET_ORDER:
                # Represents the highest available ticket number (0-indexed from top)
                self.current_ticket_number = (self.game.total_tickets - 1) if self.game.total_tickets > 0 else 0
            else:  # FORWARD_TICKET_ORDER
                # Represents the next ticket to be sold (0-indexed)
                self.current_ticket_number = 0
        else: # Should ideally not happen if game is always associated
            self.current_ticket_number = 0


    def set_as_fully_sold(self):
        """Updates current_ticket_number to reflect a fully sold book."""
        if not self.game:
            # This should not happen if the book is properly associated with a game.
            # Handle error or log, as total_tickets is needed.
            print(f"Warning: Cannot set book {self.id} as fully sold. Game association missing.")
            return

        if self.ticket_order == REVERSE_TICKET_ORDER:
            self.current_ticket_number = -1 # State after selling ticket 0
        else: # FORWARD_TICKET_ORDER
            self.current_ticket_number = self.game.total_tickets # State after selling ticket N-1
        self.is_active = False
        if not self.finish_date: # Only set finish_date if not already finished
            self.finish_date = datetime.datetime.now()


    def __repr__(self):
        return (f"<Book(id={self.id}, game_id={self.game_id}, book_number='{self.book_number}', "
                f"ticket_order='{self.ticket_order}', is_active={self.is_active}, current_ticket_number={self.current_ticket_number})>")


class SalesEntry(Base):
    """
    Represents a sales entry for a book instance.
    """
    __tablename__ = "sales_entries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    start_number = Column(Integer, nullable=False) # Book's current_ticket_number BEFORE this sale
    end_number = Column(Integer, nullable=False)   # Book's current_ticket_number AFTER this sale
    date = Column(DateTime, nullable=False, default=datetime.datetime.now)
    count = Column(Integer, nullable=False) # Calculated
    price = Column(Integer, nullable=False) # Calculated (total for this entry)

    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    book = relationship("Book", back_populates="sales_entries")

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User")

    def calculate_count_and_price(self):
        """
        Calculates and sets the 'count' and 'price' for this sales entry.
        Assumes self.book and self.book.game are populated.
        `start_number` is the book's state *before* this sale.
        `end_number` is the book's state *after* this sale.
        """
        if self.book and self.book.game:
            if self.book.ticket_order == REVERSE_TICKET_ORDER:
                # Example: start_number=99 (ticket 99 left), end_number=89 (ticket 89 left)
                # Tickets sold: 99, 98, ..., 90. Count = 99 - 89 = 10.
                # If end_number is -1 (all sold, ticket 0 was last), start=99, end=-1, count = 99 - (-1) = 100.
                if self.start_number < self.end_number: # Error condition for reverse
                    self.count = 0
                else:
                    self.count = self.start_number - self.end_number
            else: # FORWARD_TICKET_ORDER
                # Example: start_number=0 (ticket 0 is next), end_number=10 (ticket 10 is next)
                # Tickets sold: 0, 1, ..., 9. Count = 10 - 0 = 10.
                # If end_number is total_tickets (all sold, ticket N-1 was last), start=0, end=total_tickets, count = total_tickets - 0.
                if self.end_number < self.start_number: # Error condition for forward
                    self.count = 0
                else:
                    self.count = self.end_number - self.start_number

            self.price = self.count * self.book.game.price
        else:
            self.count = 0
            self.price = 0

    def __repr__(self):
        return (f"<SalesEntry(id={self.id}, book_id={self.book_id}, user_id={self.user_id}, "
                f"start_number={self.start_number}, end_number={self.end_number}, "
                f"date={self.date}, count={self.count}, price={self.price})>")

class Configuration(Base):
    __tablename__ = "configurations"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name =  Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    def get_value(self): return self.value
    def set_value(self, value): self.value = value
    def __repr__(self): return f"<Configuration(id={self.id}, name='{self.name}', value='{self.value}')>"

```
--- File Separator ---
```python
// Filename: app/services/book_service.py
from typing import List, Optional, Dict, Any, Tuple
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

    def get_book_by_game_and_book_number(self, db: Session, game_id: int, book_number_str: str) -> Optional[Book]:
        return crud_books.get_book_by_game_and_book_number(db, game_id, book_number_str)


    def activate_book(self, db: Session, book_id: int) -> Book:
        book = self.get_book_by_id(db, book_id) # Raises BookNotFoundError
        if book.is_active:
            return book # Or raise ValidationError("Book is already active.")

        if not book.game:
            raise DatabaseError(f"Book ID {book.id} is missing associated game data.")
        if book.game.is_expired:
            raise ValidationError(f"Cannot activate book for an expired game ('{book.game.name}').")

        # Check if book is already finished
        if book.ticket_order == REVERSE_TICKET_ORDER and book.current_ticket_number == -1:
            raise ValidationError(f"Cannot activate book '{book.book_number}'. It is already marked as fully sold (Reverse Order).")
        if book.ticket_order == FORWARD_TICKET_ORDER and book.game and book.current_ticket_number == book.game.total_tickets:
            raise ValidationError(f"Cannot activate book '{book.book_number}'. It is already marked as fully sold (Forward Order).")


        book.is_active = True
        book.activate_date = datetime.datetime.now()
        book.finish_date = None # Clear finish date if it was previously set for an inactive book

        # crud_books.update_book_details(db, book, {"is_active": True, "activate_date": book.activate_date, "finish_date": None})
        # The commit will be handled by the get_db_session context manager
        return book

    def activate_books_batch(self, db: Session, book_ids: List[int]) -> Tuple[List[Book], List[str]]:
        """Activates a list of books. Returns (activated_books, error_messages)."""
        activated_books: List[Book] = []
        errors: List[str] = []
        for book_id in book_ids:
            try:
                activated_book = self.activate_book(db, book_id)
                activated_books.append(activated_book)
            except (BookNotFoundError, ValidationError, DatabaseError) as e:
                errors.append(f"Book ID {book_id}: {e.message if hasattr(e, 'message') else str(e)}")
            except Exception as e_unhandled:
                errors.append(f"Book ID {book_id}: Unexpected error during activation - {str(e_unhandled)}")
        return activated_books, errors

    def deactivate_book(self, db: Session, book_id: int) -> Book:
        book = self.get_book_by_id(db, book_id)
        if not book.is_active:
            return book # Or raise ValidationError("Book is already inactive.")
        book.is_active = False
        book.finish_date = datetime.datetime.now()
        # crud_books.update_book_details(db, book, {"is_active": False, "finish_date": book.finish_date})
        return book

    def mark_book_as_fully_sold(self, db: Session, book_id: int) -> Book:
        """
        Marks a book as fully sold.
        This involves deactivating it and setting its current_ticket_number
        to the 'sold out' state.
        Does NOT create the SalesEntry record.
        """
        book = self.get_book_by_id(db, book_id) # Raises BookNotFoundError

        if not book.game: # Should have a game
            raise DatabaseError(f"Book ID {book.id} cannot be marked sold: missing associated game data.")

        # Idempotency: if already marked as fully sold (correct current_ticket_number and inactive), just return it.
        is_already_fully_sold_state = False
        if book.ticket_order == REVERSE_TICKET_ORDER and book.current_ticket_number == -1:
            is_already_fully_sold_state = True
        elif book.ticket_order == FORWARD_TICKET_ORDER and book.current_ticket_number == book.game.total_tickets:
            is_already_fully_sold_state = True

        if is_already_fully_sold_state and not book.is_active:
            return book # Already in the desired state

        # Apply the "fully sold" state changes
        book.set_as_fully_sold() # This handles current_ticket_number, is_active, and finish_date

        # Commit is handled by the context manager
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

                # Use the _initialize_current_ticket_number logic from the model by temporarily setting and calling
                # This is a bit of a hack; ideally, the model would have a method to reset based on a new order.
                # For now, direct manipulation:
                if new_ticket_order == REVERSE_TICKET_ORDER:
                    updates["current_ticket_number"] = (book.game.total_tickets - 1) if book.game.total_tickets > 0 else 0
                else:  # FORWARD_TICKET_ORDER
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

        game_cache: Dict[int, Game] = {}

        for book_entry_data in books_data:
            game_id = book_entry_data.get("game_id")
            book_number_str = book_entry_data.get("book_number_str")
            game_number_for_error_msg = book_entry_data.get("game_number_str", "N/A") # For error messages

            if game_id is None or not book_number_str:
                errors_list.append(f"Missing game_id or book_number for entry: {book_entry_data}")
                continue

            game = game_cache.get(game_id)
            if not game:
                game = crud_games.get_game_by_id(db, game_id)
                if not game:
                    errors_list.append(f"Game with ID '{game_id}' (Game No: {game_number_for_error_msg}) not found for book '{book_number_str}'.")
                    continue
                if game.is_expired:
                    errors_list.append(f"Game '{game.name}' (ID: {game_id}) is expired. Cannot add book '{book_number_str}'.")
                    continue
                game_cache[game_id] = game
            try:
                new_book = crud_books.create_book(db, game, book_number_str)
                # The Book.__init__ and _initialize_current_ticket_number now handle correct initial ticket number
                created_books_list.append(new_book)
            except (DatabaseError, ValidationError) as e:
                errors_list.append(f"Error adding book (GameNo:{game_number_for_error_msg}, BookNo:{book_number_str}): {e.message if hasattr(e, 'message') else e}")
            except Exception as e_unhandled:
                errors_list.append(f"Unexpected error for book (GameNo:{game_number_for_error_msg}, BookNo:{book_number_str}): {e_unhandled}")
        return created_books_list, errors_list

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

```
--- File Separator ---
```python
// Filename: app/services/sales_entry_service.py
import datetime
from typing import List, Dict, Tuple, Optional, Any

from sqlalchemy.orm import Session, joinedload

from app.constants import REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER, GAME_LENGTH, BOOK_LENGTH
from app.core.exceptions import ValidationError, DatabaseError, GameNotFoundError
from app.core.models import Book, SalesEntry, Game as GameModel # Added GameModel
from app.data import crud_books, crud_games, crud_sales_entries


class SalesEntryService:
    def get_active_books_for_sales_display(self, db: Session) -> List[Book]:
        return db.query(Book).options(
            joinedload(Book.game)
        ).filter(
            Book.is_active == True,
            GameModel.is_expired == False # Ensure game is also not expired
        ).join(Book.game).order_by(Book.game_id, Book.book_number).all()

    def get_or_create_book_for_sale(self, db: Session, game_number_str: str, book_number_str: str) -> Book:
        if not (game_number_str.isdigit() and len(game_number_str) == GAME_LENGTH):
            raise ValidationError(f"Game Number for scan must be {GAME_LENGTH} digits.")
        if not (book_number_str.isdigit() and len(book_number_str) == BOOK_LENGTH):
            raise ValidationError(f"Book Number for scan must be {BOOK_LENGTH} digits.")

        game_num_int = int(game_number_str)
        game = crud_games.get_game_by_game_number(db, game_num_int)

        if not game:
            raise GameNotFoundError(f"Game number '{game_number_str}' not found.")
        if game.is_expired:
            raise ValidationError(f"Game '{game.name}' (No: {game_number_str}) is expired. Cannot process sales.")

        book = db.query(Book).options(joinedload(Book.game)).filter(Book.game_id == game.id, Book.book_number == book_number_str).first()

        if not book:
            try:
                # crud_books.create_book correctly initializes current_ticket_number via Book.__init__
                new_book = crud_books.create_book(db, game, book_number_str)
                new_book.is_active = True # Activate new book for sales
                new_book.activate_date = datetime.datetime.now()
                db.flush() # Ensure new_book gets an ID if not committed yet by context manager
                db.refresh(new_book, attribute_names=['game']) # Eager load game for the new book
                print(f"SalesEntryService: Created/activated new book: ID {new_book.id}, Num {new_book.book_number}, Initial Ticket: {new_book.current_ticket_number}")
                return new_book
            except (DatabaseError, ValidationError) as e:
                raise DatabaseError(f"Could not create book {game_number_str}-{book_number_str} for sale: {e.message if hasattr(e, 'message') else e}")
        else: # Book exists
            if not book.game: db.refresh(book, attribute_names=['game']) # Ensure game is loaded
            if not book.is_active:
                # Before activating, ensure the book is not already finished
                if book.ticket_order == REVERSE_TICKET_ORDER and book.current_ticket_number == -1:
                    raise ValidationError(f"Book '{book.book_number}' is already sold out (Reverse). Cannot use for sales.")
                if book.ticket_order == FORWARD_TICKET_ORDER and book.game and book.current_ticket_number == book.game.total_tickets:
                    raise ValidationError(f"Book '{book.book_number}' is already sold out (Forward). Cannot use for sales.")

                book.is_active = True
                book.activate_date = datetime.datetime.now()
                book.finish_date = None # Clear finish date if reactivating
                print(f"SalesEntryService: Activated existing book for sale: {book.book_number}, Current Ticket: {book.current_ticket_number}")
            return book

    def create_sales_entry_for_full_book(self, db: Session, book: Book, user_id: int) -> SalesEntry:
        """
        Creates a SalesEntry record for a book that has been marked as fully sold.
        Assumes the book's current_ticket_number and status have already been updated
        by BookService.mark_book_as_fully_sold.
        """
        if not book.game:
            raise DatabaseError(f"Book ID {book.id} is missing game data for full sale entry.")

        # Determine start_number (state before this "full sale" action)
        # This is tricky if the book was partially sold before.
        # For simplicity, if we are calling this, we assume the "start" was its original pristine state.
        original_start_number = 0
        if book.ticket_order == REVERSE_TICKET_ORDER:
            original_start_number = book.game.total_tickets -1 # Highest ticket number index
        else: # FORWARD_TICKET_ORDER
            original_start_number = 0 # Lowest ticket number index (first to be sold)

        # end_number is the state *after* this "full sale" action
        final_end_number = book.current_ticket_number # This should be -1 or total_tickets

        sales_entry = SalesEntry(
            book_id=book.id,
            user_id=user_id,
            start_number=original_start_number, # Representing the sale of ALL tickets from initial state
            end_number=final_end_number,         # Representing the final state after all tickets sold
            date=datetime.datetime.now(),
            book=book # Associate for calculation
        )
        sales_entry.calculate_count_and_price()

        if sales_entry.count != book.game.total_tickets:
            # This might indicate an issue or an edge case not handled by original_start_number logic.
            # For now, log a warning. The calculation should make count = total_tickets.
            print(f"Warning: Full book sale for Book ID {book.id} resulted in count {sales_entry.count}, expected {book.game.total_tickets}.")
            # Override count if necessary, though calculate_count_and_price should be robust.
            # sales_entry.count = book.game.total_tickets
            # sales_entry.price = sales_entry.count * book.game.price

        return crud_sales_entries.create_sales_entry(db, sales_entry)


    def process_and_save_sales_batch(
            self, db: Session, user_id: int, sales_item_details: List[Dict[str, Any]]
    ) -> Tuple[int, int, List[str]]:
        successful_sales_count = 0
        updated_books_count = 0
        error_messages: List[str] = []

        for detail_idx, detail in enumerate(sales_item_details):
            book_id = detail.get("book_db_id")
            book_state_at_ui_load = detail.get("db_current_ticket_no") # This is crucial
            ui_target_state_str = detail.get("ui_new_ticket_no_str")
            all_sold_confirmed_by_ui = detail.get("all_tickets_sold_confirmed", False)

            book: Optional[Book] = db.query(Book).options(joinedload(Book.game)).filter(Book.id == book_id).first()

            if not book or not book.game:
                error_messages.append(f"Item {detail_idx+1}: Book ID {book_id} or its game data not found.")
                continue

            final_book_ticket_number_to_set: int
            is_valid_target_state = False

            if all_sold_confirmed_by_ui:
                if book.ticket_order == REVERSE_TICKET_ORDER:
                    final_book_ticket_number_to_set = -1
                else: # FORWARD_TICKET_ORDER
                    final_book_ticket_number_to_set = book.game.total_tickets
                is_valid_target_state = True
            elif ui_target_state_str is not None and (ui_target_state_str == "-1" or ui_target_state_str.isdigit()): # Allow -1
                try:
                    parsed_num = int(ui_target_state_str)
                    # Validate range based on book's order and current state *before* this specific sale transaction.
                    # The book_state_at_ui_load is the book.current_ticket_number *before* this sale.
                    is_range_ok = False
                    if book.ticket_order == REVERSE_TICKET_ORDER:
                        # Can go from book_state_at_ui_load down to -1.
                        # parsed_num must be <= book_state_at_ui_load AND >= -1.
                        is_range_ok = (-1 <= parsed_num <= book_state_at_ui_load)
                    else: # FORWARD_TICKET_ORDER
                        # Can go from book_state_at_ui_load up to total_tickets.
                        # parsed_num must be >= book_state_at_ui_load AND <= book.game.total_tickets.
                        is_range_ok = (book_state_at_ui_load <= parsed_num <= book.game.total_tickets)

                    if is_range_ok:
                        final_book_ticket_number_to_set = parsed_num
                        is_valid_target_state = True
                    else:
                        range_hint = f"between -1 and {book_state_at_ui_load}" if book.ticket_order == REVERSE_TICKET_ORDER else f"between {book_state_at_ui_load} and {book.game.total_tickets}"
                        error_messages.append(f"Item {detail_idx+1}: Invalid target ticket '{ui_target_state_str}' for Book {book.book_number}. Expected {range_hint}.")
                except ValueError:
                     error_messages.append(f"Item {detail_idx+1}: Non-integer target ticket '{ui_target_state_str}' for Book {book.book_number}.")
            else:
                error_messages.append(f"Item {detail_idx+1}: No valid ticket entry for Book {book.book_number} and not 'all sold'. Skipped.")


            if not is_valid_target_state:
                continue

            # For SalesEntry: start_number is book's state before this sale, end_number is book's state after this sale.
            sales_entry_start_number = book_state_at_ui_load
            sales_entry_end_number = final_book_ticket_number_to_set

            calculated_tickets_for_this_entry = 0
            if book.ticket_order == REVERSE_TICKET_ORDER:
                if sales_entry_start_number >= sales_entry_end_number:
                    calculated_tickets_for_this_entry = sales_entry_start_number - sales_entry_end_number
            else: # FORWARD_TICKET_ORDER
                if sales_entry_end_number >= sales_entry_start_number:
                    calculated_tickets_for_this_entry = sales_entry_end_number - sales_entry_start_number

            if calculated_tickets_for_this_entry < 0:
                error_messages.append(f"Item {detail_idx+1}: Negative sales calc for Book {book.book_number}. Start: {sales_entry_start_number}, End: {sales_entry_end_number}. Skipped.")
                continue

            if calculated_tickets_for_this_entry > 0 or all_sold_confirmed_by_ui : # Only create entry if actual sales or explicit all_sold
                try:
                    new_sales_entry = SalesEntry(
                        book_id=book.id, user_id=user_id,
                        start_number=sales_entry_start_number,
                        end_number=sales_entry_end_number,
                        date=datetime.datetime.now(), book=book
                    )
                    new_sales_entry.calculate_count_and_price()

                    if new_sales_entry.count != calculated_tickets_for_this_entry:
                         print(f"Warning: Discrepancy in tickets for Book {book.book_number}. Service: {calculated_tickets_for_this_entry}, Model: {new_sales_entry.count}. Using Model.")

                    if new_sales_entry.count >= 0 : # Allow 0 count sales if 'all_sold' was confirmed for an already finished book
                        crud_sales_entries.create_sales_entry(db, new_sales_entry)
                        successful_sales_count += 1
                    elif new_sales_entry.count < 0: # Should be prevented by earlier checks
                        error_messages.append(f"Item {detail_idx+1}: SalesEntry model calculated negative count for Book {book.book_number}. Skipped sales record.")
                        continue # Skip sales record but still update book below if needed

                except Exception as e_sales:
                    error_messages.append(f"Item {detail_idx+1}: Error creating sales entry for Book {book.book_number}: {e_sales}")
                    continue # If sales entry fails, maybe don't update book? Or make it configurable. For now, continue.

            # Update Book state based on final_book_ticket_number_to_set
            try:
                book.current_ticket_number = final_book_ticket_number_to_set
                updated_books_count += 1 # Count as updated even if only current_ticket_number changed

                is_book_finished_after_this_sale = False
                if book.ticket_order == REVERSE_TICKET_ORDER and final_book_ticket_number_to_set == -1:
                    is_book_finished_after_this_sale = True
                elif book.ticket_order == FORWARD_TICKET_ORDER and final_book_ticket_number_to_set == book.game.total_tickets:
                    is_book_finished_after_this_sale = True

                if all_sold_confirmed_by_ui or is_book_finished_after_this_sale:
                    if book.is_active: # Only deactivate if it was active
                        book.is_active = False
                        book.finish_date = datetime.datetime.now()
                        print(f"Book {book.book_number} deactivated after sales processing.")
                    # If it's already inactive but we confirm all_sold, ensure finish_date is set
                    elif not book.finish_date :
                        book.finish_date = datetime.datetime.now()


            except Exception as e_book:
                error_messages.append(f"Item {detail_idx+1}: Error updating Book {book.book_number} state: {e_book}")

        return successful_sales_count, updated_books_count, error_messages

```
--- File Separator ---
```python
// Filename: app/ui/components/common/scan_input_handler.py
import flet as ft
from typing import Callable, Dict, Optional, Tuple

from app.constants import GAME_LENGTH, BOOK_LENGTH, TICKET_LENGTH, MIN_REQUIRED_SCAN_LENGTH_WITH_TICKET, MIN_REQUIRED_SCAN_LENGTH


class ScanInputHandler:
    """
    Handles logic for a scan input TextField, including parsing and validation.
    This is not a Flet Control, but a helper to be used with a ft.TextField.
    """
    def __init__(
        self,
        scan_text_field: ft.TextField,
        on_scan_complete: Callable[[Dict[str, str]], None], # Callback with parsed data: {'game_no', 'book_no', 'ticket_no'?}
        on_scan_error: Callable[[str], None], # Callback with error message
        require_ticket: bool = False, # If true, expects game+book+ticket
        auto_clear_on_complete: bool = True,
        auto_focus_on_complete: bool = True,
    ):
        self.scan_text_field = scan_text_field
        self.on_scan_complete = on_scan_complete
        self.on_scan_error = on_scan_error
        self.require_ticket = require_ticket
        self.auto_clear_on_complete = auto_clear_on_complete
        self.auto_focus_on_complete = auto_focus_on_complete

        self.expected_length = MIN_REQUIRED_SCAN_LENGTH_WITH_TICKET if require_ticket else MIN_REQUIRED_SCAN_LENGTH

        # Attach the handler to the TextField's on_change and on_submit
        self.scan_text_field.on_change = self._handle_input_change
        self.scan_text_field.on_submit = self._handle_input_submit # For manual Enter press

    def _parse_scan_data(self, scan_value: str) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
        """
        Parses the scan value into game, book, and optionally ticket numbers.
        Returns (parsed_data_dict, error_message_or_none).
        """
        scan_value = scan_value.strip()
        
        if len(scan_value) < self.expected_length:
            return None, f"Scan input too short. Expected {self.expected_length} chars, got {len(scan_value)}."

        # Truncate to expected length to avoid issues with over-scans if QR has more data
        scan_value = scan_value[:self.expected_length]

        game_no_str = scan_value[:GAME_LENGTH]
        book_no_str = scan_value[GAME_LENGTH : GAME_LENGTH + BOOK_LENGTH]
        
        parsed_data = {}

        if not (game_no_str.isdigit() and len(game_no_str) == GAME_LENGTH):
            return None, f"Invalid Game No. format: '{game_no_str}'. Expected {GAME_LENGTH} digits."
        parsed_data['game_no'] = game_no_str

        if not (book_no_str.isdigit() and len(book_no_str) == BOOK_LENGTH):
            return None, f"Invalid Book No. format: '{book_no_str}'. Expected {BOOK_LENGTH} digits."
        parsed_data['book_no'] = book_no_str

        if self.require_ticket:
            if len(scan_value) < GAME_LENGTH + BOOK_LENGTH + TICKET_LENGTH:
                 return None, f"Scan input too short for ticket. Expected {TICKET_LENGTH} more chars."
            ticket_no_str = scan_value[GAME_LENGTH + BOOK_LENGTH : GAME_LENGTH + BOOK_LENGTH + TICKET_LENGTH]
            if not (ticket_no_str.isdigit() and len(ticket_no_str) == TICKET_LENGTH):
                return None, f"Invalid Ticket No. format: '{ticket_no_str}'. Expected {TICKET_LENGTH} digits."
            parsed_data['ticket_no'] = ticket_no_str
        
        return parsed_data, None


    def _process_input(self, current_value: str):
        """Core logic to process the input value from the TextField."""
        if len(current_value) >= self.expected_length:
            parsed_data, error_msg = self._parse_scan_data(current_value)

            if error_msg:
                self.on_scan_error(error_msg)
                # Optionally, clear field on error too, or let user correct
                # self.scan_text_field.value = "" 
            elif parsed_data:
                self.on_scan_complete(parsed_data)
            
            if self.auto_clear_on_complete or error_msg : # Clear on success or if there was an error during parse attempt
                self.scan_text_field.value = ""
            
            if self.scan_text_field.page:
                self.scan_text_field.update()
            
            if self.auto_focus_on_complete and self.scan_text_field.page:
                 self.scan_text_field.focus()


    def _handle_input_change(self, e: ft.ControlEvent):
        """Attached to TextField's on_change."""
        current_value = e.control.value.strip() if e.control.value else ""
        # Process only if length meets criteria, typical for scanner auto-submit behavior
        if len(current_value) >= self.expected_length:
            self._process_input(current_value)

    def _handle_input_submit(self, e: ft.ControlEvent):
        """Attached to TextField's on_submit (e.g., Enter key)."""
        current_value = e.control.value.strip() if e.control.value else ""
        # Process regardless of length if submitted, but parsing will still check length
        self._process_input(current_value)

    def clear_input(self):
        self.scan_text_field.value = ""
        if self.scan_text_field.page:
            self.scan_text_field.update()

    def focus_input(self):
        if self.scan_text_field.page:
            self.scan_text_field.focus()

```
--- File Separator ---
```python
// Filename: app/ui/components/dialogs/book_action_dialog.py
import flet as ft
from typing import List, Callable, Optional, Dict, Any

from app.constants import (
    GAME_LENGTH, BOOK_LENGTH, TICKET_LENGTH,
    MIN_REQUIRED_SCAN_LENGTH, MIN_REQUIRED_SCAN_LENGTH_WITH_TICKET,
    BOOK_ACTION_ADD_NEW, BOOK_ACTION_FULL_SALE, BOOK_ACTION_ACTIVATE
)
from app.core.models import User, Game as GameModel
from app.services.game_service import GameService
from app.data.database import get_db_session
from app.core.exceptions import ValidationError, DatabaseError, GameNotFoundError
from app.data import crud_games # For direct game fetching
from app.ui.components.widgets import NumberDecimalField
from app.ui.components.common.scan_input_handler import ScanInputHandler


class TempBookActionItem:
    """Represents a book temporarily listed in the dialog for an action."""
    def __init__(self, game_model: GameModel, book_number_str: str, ticket_number_str: Optional[str] = None):
        self.game_id: int = game_model.id
        self.game_number_str: str = str(game_model.game_number).zfill(GAME_LENGTH)
        self.book_number_str: str = book_number_str
        self.ticket_number_str: Optional[str] = ticket_number_str # Relevant for some actions

        self.game_name: str = game_model.name
        self.game_price: int = game_model.price
        self.total_tickets: int = game_model.total_tickets
        self.default_ticket_order: str = game_model.default_ticket_order
        self.is_game_expired: bool = game_model.is_expired

        self.unique_key: str = f"{self.game_number_str}-{self.book_number_str}"
        # Store the original GameModel if needed for more complex ops later by the callback
        self.game_model_ref: GameModel = game_model


    def to_datarow(self, on_remove_callback: Callable[['TempBookActionItem'], None], action_type: str) -> ft.DataRow:
        details_parts = [
            f"Game: {self.game_name} ({self.game_number_str})",
            f"Price: ${self.game_price}",
            f"Total Tickets: {self.total_tickets}",
        ]
        if self.ticket_number_str:
            details_parts.append(f"Ticket: {self.ticket_number_str}")

        action_specific_display = ""
        if action_type == BOOK_ACTION_FULL_SALE:
            action_specific_display = f"Value: ${self.game_price * self.total_tickets}"
        elif action_type == BOOK_ACTION_ACTIVATE:
            action_specific_display = f"Order: {self.default_ticket_order.capitalize()}"
        elif action_type == BOOK_ACTION_ADD_NEW:
             action_specific_display = f"Order: {self.default_ticket_order.capitalize()}"


        return ft.DataRow(cells=[
            ft.DataCell(ft.Text(self.book_number_str, weight=ft.FontWeight.BOLD)),
            ft.DataCell(ft.Text(" | ".join(details_parts))),
            ft.DataCell(ft.Text(action_specific_display)),
            ft.DataCell(ft.IconButton(ft.Icons.REMOVE_CIRCLE_OUTLINE, icon_color=ft.Colors.RED_ACCENT_700,
                                      on_click=lambda e: on_remove_callback(self), tooltip="Remove from list"))
        ])

    def to_submission_dict(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "game_number_str": self.game_number_str, # For messages
            "book_number_str": self.book_number_str,
            "ticket_number_str": self.ticket_number_str,
            "game_model_ref": self.game_model_ref # Pass the model for convenience in callbacks
        }


class BookActionDialog(ft.AlertDialog):
    """
    A generic dialog for performing actions on a list of books selected via scan or manual entry.
    """
    def __init__(
        self,
        page_ref: ft.Page,
        current_user_ref: User, # For batch callback
        dialog_title: str,
        action_button_text: str,
        action_type: str, # e.g. BOOK_ACTION_ADD_NEW, BOOK_ACTION_FULL_SALE, BOOK_ACTION_ACTIVATE
        on_confirm_batch_callback: Callable[[Session, List[Dict[str, Any]], User], Tuple[int, int, List[str]]], # (db, items_to_process, current_user) -> (success_count, failure_count, error_messages)
        game_service: GameService, # To fetch game details
        require_ticket_scan: bool = False,
        dialog_height_ratio: float = 0.85,
        dialog_width: int = 650,
    ):
        super().__init__() # Call AlertDialog constructor

        self.page = page_ref
        self.current_user = current_user_ref
        self.dialog_title_text = dialog_title
        self.action_button_text = action_button_text
        self.action_type = action_type
        self.on_confirm_batch_callback = on_confirm_batch_callback
        self.game_service = game_service
        self.require_ticket_scan = require_ticket_scan # If true, scan input expects ticket

        self._temp_action_items_list: List[TempBookActionItem] = []

        self.modal = True
        self.title = ft.Text(self.dialog_title_text, style=ft.TextThemeStyle.HEADLINE_SMALL, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
        
        self.total_items_label = ft.Text("Books in List: 0", weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY)
        self.dialog_error_text = ft.Text("", color=ft.Colors.RED_ACCENT_700, visible=False, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)

        # --- Scan Input ---
        scan_field_label = "Scan Full Code"
        scan_field_hint = f"Game({GAME_LENGTH}) + Book({BOOK_LENGTH})"
        if self.require_ticket_scan:
            scan_field_label = "Scan Full Code with Ticket"
            scan_field_hint += f" + Ticket({TICKET_LENGTH})"

        self.scanner_text_field = ft.TextField(
            label=scan_field_label, hint_text=scan_field_hint,
            autofocus=True, height=50, border_radius=8, prefix_icon=ft.Icons.QR_CODE_SCANNER_ROUNDED, expand=True
        )
        self.scan_input_handler = ScanInputHandler(
            scan_text_field=self.scanner_text_field,
            on_scan_complete=self._handle_scan_complete,
            on_scan_error=self._show_dialog_error,
            require_ticket=self.require_ticket_scan
        )

        # --- Manual Input ---
        self.manual_game_no_field = NumberDecimalField(label="Game No.", hint_text=f"{GAME_LENGTH} digits", width=120, max_length=GAME_LENGTH, is_integer_only=True, border_radius=8, height=50)
        self.manual_book_no_field = ft.TextField(label="Book No.", hint_text=f"{BOOK_LENGTH} digits", width=180, max_length=BOOK_LENGTH, border_radius=8, input_filter=ft.InputFilter(r"[0-9]"), height=50)
        
        # Ticket field for manual entry if needed (conditionally visible)
        self.manual_ticket_no_field = ft.TextField(label="Ticket No.", hint_text=f"{TICKET_LENGTH} digits", width=120, max_length=TICKET_LENGTH, border_radius=8, input_filter=ft.InputFilter(r"[0-9]"), height=50, visible=self.require_ticket_scan)
        
        self.add_manual_button = ft.Button("Add Manual", icon=ft.Icons.ADD_TO_QUEUE_ROUNDED, on_click=self._handle_manual_add_click, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)))

        # --- Table for Temporary Items ---
        self.items_datatable = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Book #", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Details", weight=ft.FontWeight.BOLD, expand=2)), # Give more space to details
                ft.DataColumn(ft.Text("Action Info", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Remove", weight=ft.FontWeight.BOLD), numeric=True),
            ], rows=[], heading_row_height=35, data_row_min_height=40, column_spacing=15, expand=True
        )

        # --- Dialog Layout ---
        scanner_section = ft.Container(
            ft.Column([ft.Text("Scan Barcode", weight=ft.FontWeight.W_500, size=15, color=ft.Colors.PRIMARY), self.scanner_text_field],
                      spacing=8, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
            padding=ft.padding.symmetric(vertical=10, horizontal=12), border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=ft.border_radius.all(10), bgcolor=ft.Colors.SURFACE_VARIANT,
        )
        manual_entry_row_controls = [self.manual_game_no_field, self.manual_book_no_field]
        if self.require_ticket_scan:
            manual_entry_row_controls.append(self.manual_ticket_no_field)
        manual_entry_row_controls.append(self.add_manual_button)

        manual_section = ft.Container(
            ft.Column([ft.Text("Manual Entry", weight=ft.FontWeight.W_500, size=15, color=ft.Colors.PRIMARY),
                       ft.Row(manual_entry_row_controls, alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.END, spacing=10)],
                      spacing=8),
            padding=ft.padding.symmetric(vertical=10, horizontal=12), border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=ft.border_radius.all(10), bgcolor=ft.Colors.SURFACE_VARIANT,
        )
        or_separator = ft.Row(
            [ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT, expand=True),
             ft.Container(ft.Text("OR", weight=ft.FontWeight.BOLD, color=ft.Colors.OUTLINE), padding=ft.padding.symmetric(horizontal=8)),
             ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT, expand=True)],
            alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
        table_scroll_container = ft.Container(
            content=ft.Column([self.items_datatable], scroll=ft.ScrollMode.ADAPTIVE),
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT), border_radius=ft.border_radius.all(8),
            padding=ft.padding.all(5), expand=True,
        )
        
        dialog_content_column = ft.Column(
            [
                scanner_section, or_separator, manual_section,
                self.dialog_error_text,
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                ft.Row([ft.Text("Books Queued for Action:", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.W_600, color=ft.Colors.PRIMARY), self.total_items_label],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                table_scroll_container,
            ],
            spacing=10, expand=True,
        )

        self.content = ft.Container(
            content=dialog_content_column,
            width=dialog_width,
            height=self.page.height * dialog_height_ratio if self.page.height and self.page.height * dialog_height_ratio > 400 else 600,
            padding=ft.padding.symmetric(vertical=12, horizontal=15),
            border_radius=ft.border_radius.all(10)
        )
        self.actions = [
            ft.TextButton("Cancel", on_click=self._handle_cancel_click, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))),
            ft.FilledButton(self.action_button_text, on_click=self._handle_confirm_click, icon=ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)))
        ]
        self.actions_alignment = ft.MainAxisAlignment.END
        self.shape = ft.RoundedRectangleBorder(radius=10)

    def _show_dialog_error(self, message: str):
        self.dialog_error_text.value = message
        self.dialog_error_text.visible = True
        if self.dialog_error_text.page: self.dialog_error_text.update()
        if self.page: self.page.update() # Update dialog or page to show error

    def _clear_dialog_error(self):
        self.dialog_error_text.value = ""
        self.dialog_error_text.visible = False
        if self.dialog_error_text.page: self.dialog_error_text.update()

    def _update_dialog_table_and_counts(self):
        self.items_datatable.rows = [
            item.to_datarow(self._remove_item_from_list, self.action_type) for item in self._temp_action_items_list
        ]
        self.total_items_label.value = f"Books in List: {len(self._temp_action_items_list)}"
        if self.items_datatable.page: self.items_datatable.update()
        if self.total_items_label.page: self.total_items_label.update()
        if self.page: self.page.update()

    def _remove_item_from_list(self, item_to_remove: TempBookActionItem):
        self._temp_action_items_list = [item for item in self._temp_action_items_list if item.unique_key != item_to_remove.unique_key]
        self._update_dialog_table_and_counts()

    def _add_item_to_action_list(self, game_no_str: str, book_no_str: str, ticket_no_str: Optional[str] = None):
        self._clear_dialog_error()
        game_model: Optional[GameModel] = None
        try:
            # Basic validation (ScanInputHandler also does this, but good for manual)
            if not (game_no_str and game_no_str.isdigit() and len(game_no_str) == GAME_LENGTH):
                raise ValidationError(f"Game Number must be {GAME_LENGTH} digits.")
            if not (book_no_str and book_no_str.isdigit() and len(book_no_str) == BOOK_LENGTH):
                raise ValidationError(f"Book Number must be {BOOK_LENGTH} digits.")
            if self.require_ticket_scan and not (ticket_no_str and ticket_no_str.isdigit() and len(ticket_no_str) == TICKET_LENGTH):
                 raise ValidationError(f"Ticket Number must be {TICKET_LENGTH} digits.")

            game_num_int = int(game_no_str)
            with get_db_session() as db: # Fetch game details to display
                game_model = crud_games.get_game_by_game_number(db, game_num_int)

            if not game_model:
                raise GameNotFoundError(f"Game number '{game_no_str}' not found.")

            # Action-specific validations
            if self.action_type == BOOK_ACTION_ADD_NEW and game_model.is_expired:
                raise ValidationError(f"Game '{game_model.name}' (No: {game_no_str}) is expired. Cannot add new books.")
            
            # TODO: Add more specific validations for FULL_SALE (e.g., book exists, not already sold out)
            # TODO: Add more specific validations for ACTIVATE (e.g., book exists, not active, game not expired)
            # These might be better handled by the on_confirm_batch_callback for more detailed feedback.
            # For now, the dialog mainly ensures Game exists and is not expired (for ADD_NEW).

            unique_key_to_add = f"{game_no_str}-{book_no_str}"
            if any(item.unique_key == unique_key_to_add for item in self._temp_action_items_list):
                raise ValidationError(f"Book {unique_key_to_add} is already in the list.")

            temp_item = TempBookActionItem(game_model, book_no_str, ticket_no_str)
            self._temp_action_items_list.insert(0, temp_item) # Add to top
            self._update_dialog_table_and_counts()

            # Clear manual fields on success
            self.manual_game_no_field.clear()
            self.manual_book_no_field.value = ""
            if self.manual_book_no_field.page: self.manual_book_no_field.update()
            if self.require_ticket_scan and self.manual_ticket_no_field:
                self.manual_ticket_no_field.value = ""
                if self.manual_ticket_no_field.page: self.manual_ticket_no_field.update()
            
            self.scan_input_handler.focus_input() # Focus scanner after successful add

        except (GameNotFoundError, ValidationError, DatabaseError) as e:
            self._show_dialog_error(str(e.message if hasattr(e, 'message') else e))
        except ValueError: # int conversion
            self._show_dialog_error(f"Invalid Game Number format. Must be {GAME_LENGTH} digits.")
        except Exception as ex_unhandled:
            self._show_dialog_error(f"Unexpected error: {ex_unhandled}")

    def _handle_scan_complete(self, parsed_data: Dict[str, str]):
        game_no = parsed_data.get('game_no', '')
        book_no = parsed_data.get('book_no', '')
        ticket_no = parsed_data.get('ticket_no') if self.require_ticket_scan else None
        self._add_item_to_action_list(game_no, book_no, ticket_no)

    def _handle_manual_add_click(self, e: ft.ControlEvent):
        game_no_str = self.manual_game_no_field.get_value_as_str()
        book_no_str = self.manual_book_no_field.value.strip() if self.manual_book_no_field.value else ""
        ticket_no_str = None
        if self.require_ticket_scan and self.manual_ticket_no_field:
            ticket_no_str = self.manual_ticket_no_field.value.strip() if self.manual_ticket_no_field.value else ""
        
        self._add_item_to_action_list(game_no_str, book_no_str, ticket_no_str)


    def _handle_confirm_click(self, e: ft.ControlEvent):
        self._clear_dialog_error()
        if not self._temp_action_items_list:
            self._show_dialog_error("No books in the list to process.")
            return

        items_to_submit = [item.to_submission_dict() for item in self._temp_action_items_list]
        
        try:
            with get_db_session() as db:
                success_count, failure_count, error_messages = self.on_confirm_batch_callback(
                    db, items_to_submit, self.current_user
                )
            
            self.page.close(self) # Close self (the dialog)

            final_message = f"{success_count} book(s) processed successfully."
            if failure_count > 0:
                final_message += f" {failure_count} book(s) failed."
            if error_messages:
                # For simplicity, logging errors. UI could show them in a new dialog/snackbar.
                print(f"Book Action Dialog - Batch Errors for {self.dialog_title_text}:")
                for err_msg in error_messages:
                    print(f"- {err_msg}")
                final_message += " (See console for details on failures)."
            
            self.page.open(ft.SnackBar(ft.Text(final_message), open=True, duration=5000 if error_messages else 3000))
            
            # Caller view should refresh its data if needed (e.g. BookManagementView's table)
            # This is typically done by the caller after the dialog closes.
            # If this dialog needs to trigger a refresh directly, it would need a callback.

        except Exception as ex_batch:
            # This catches errors in the callback itself or during DB session
            self._show_dialog_error(f"Error during batch processing: {ex_batch}")
            # Dialog remains open for user to see the error or retry.
            # self.page.update() # Ensure error is shown

    def _handle_cancel_click(self, e: ft.ControlEvent):
        self.page.close(self)

    def open_dialog(self):
        """Assigns self to page.dialog and opens it."""
        self.page.dialog = self
        self.page.open(self)
        # Slight delay to ensure dialog is rendered before focusing
        ft.threading.Thread(target=self._delayed_focus).start()

    def _delayed_focus(self):
        import time
        time.sleep(0.1) # Small delay
        if self.scanner_text_field and self.scanner_text_field.page:
            self.scanner_text_field.focus()


```
--- File Separator ---
```python
// Filename: app/ui/components/tables/sales_entry_items_table.py
import flet as ft
from typing import List, Callable, Optional, Dict
from app.core.models import Book as BookModel
from app.services.sales_entry_service import SalesEntryService
from app.data.database import get_db_session
from .sales_entry_item_data import SalesEntryItemData

class SalesEntryItemsTable(ft.Container):
    def __init__(self,
                 page_ref: ft.Page,
                 sales_entry_service: SalesEntryService,
                 on_item_change_callback: Callable[[SalesEntryItemData], None],
                 on_all_items_loaded_callback: Callable[[List[SalesEntryItemData]], None]
                 ):
        super().__init__(expand=True)
        self.page = page_ref
        self.sales_entry_service = sales_entry_service
        self.on_item_change_callback = on_item_change_callback
        self.on_all_items_loaded_callback = on_all_items_loaded_callback

        self.sales_items_data_list: List[SalesEntryItemData] = []
        self.sales_items_map: Dict[str, SalesEntryItemData] = {} # Maps unique_id to SalesEntryItemData

        self.datatable = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Book Details", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Price", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Current Ticket", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("New Ticket #", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Tickets Sold", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Amount", weight=ft.FontWeight.BOLD), numeric=True),
            ],
            rows=[],
            column_spacing=15,
            heading_row_height=40,
            data_row_max_height=55,
            expand=True,
        )
        self.content = ft.Column(
            [self.datatable],
            scroll=ft.ScrollMode.ADAPTIVE,
            expand=True
        )

    def _internal_item_change_handler(self, item_data: SalesEntryItemData):
        # When an item's internal state changes (e.g., textfield edit), update its row
        self.update_datarow_for_item(item_data.unique_id) # This will refresh the specific row
        self.on_item_change_callback(item_data) # Notify view for totals update

    def load_initial_active_books(self):
        self.sales_items_data_list = []
        self.sales_items_map = {}
        initial_rows = []
        try:
            with get_db_session() as db:
                active_books: List[BookModel] = self.sales_entry_service.get_active_books_for_sales_display(db)

            for book_model in active_books:
                if book_model.id is None: continue
                item_data = SalesEntryItemData(
                    book_model=book_model,
                    on_change_callback=self._internal_item_change_handler
                )
                self.sales_items_data_list.append(item_data)
                self.sales_items_map[item_data.unique_id] = item_data
                # initial_rows.append(item_data.to_datarow()) # Rows built at the end

            # Sort by game_number, then book_number initially
            self.sales_items_data_list.sort(key=lambda x: (x.book_model.game.game_number, x.book_number))
            self.datatable.rows = [item.to_datarow() for item in self.sales_items_data_list]
            
            self.on_all_items_loaded_callback(self.sales_items_data_list) # Notify view
        except Exception as e:
            print(f"Error loading active books for sales table: {e}")
            self.datatable.rows = [ft.DataRow(cells=[ft.DataCell(ft.Text(f"Error loading books: {e}", color=ft.Colors.ERROR))])]

        if self.page and self.page.controls: self.page.update()


    def add_or_update_book_for_sale(self, book_model: BookModel, scanned_ticket_str: Optional[str] = None) -> Optional[SalesEntryItemData]:
        if book_model.id is None:
            # ... (error handling as before)
            return None

        unique_id = f"book-{book_model.id}"
        item_data = self.sales_items_map.get(unique_id)
        
        is_new_item = False
        if item_data:  # Book ALREADY IN TABLE
            print(f"SalesTable: Updating existing item {unique_id} with scan: {scanned_ticket_str if scanned_ticket_str else 'No Ticket Scan'}")
            # Remove from current position to re-insert at top
            self.sales_items_data_list = [item for item in self.sales_items_data_list if item.unique_id != unique_id]
            
            # Update existing item_data's model and critical fields
            item_data.book_model = book_model
            item_data.db_current_ticket_no = book_model.current_ticket_number
            item_data.game_name = book_model.game.name if book_model.game else item_data.game_name
            item_data.game_price = book_model.game.price if book_model.game else item_data.game_price
            item_data.game_total_tickets = book_model.game.total_tickets if book_model.game else item_data.game_total_tickets
            item_data.ticket_order = book_model.ticket_order

            if scanned_ticket_str:
                item_data.update_scanned_ticket_number(scanned_ticket_str) # This calls _calculate_sales and on_change_callback
            else:
                item_data._calculate_sales() # Recalculate if no scan but model might have changed

        else:  # Book NOT IN TABLE YET
            is_new_item = True
            print(f"SalesTable: Adding new item {unique_id} with scan: {scanned_ticket_str if scanned_ticket_str else 'No Ticket Scan'}")
            item_data = SalesEntryItemData(
                book_model=book_model,
                on_change_callback=self._internal_item_change_handler
            )
            if scanned_ticket_str:
                item_data.update_scanned_ticket_number(scanned_ticket_str)
            else:
                item_data._calculate_sales() # Ensure initial calculation

            self.sales_items_map[unique_id] = item_data
        
        # Add/Re-add item_data to the beginning of the list
        self.sales_items_data_list.insert(0, item_data)
        
        # Rebuild all DataTable rows to reflect the new order
        self.datatable.rows = [item.to_datarow() for item in self.sales_items_data_list]

        # Notify the main view about the change for total updates, especially if it was a new item
        if is_new_item : # Or always call if totals might change due to scan on existing item
            self.on_item_change_callback(item_data) 

        if self.page and self.page.controls: self.page.update()
        return item_data

    def update_datarow_for_item(self, unique_item_id: str):
        """Updates a specific row in the DataTable if its underlying data changed."""
        item_data = self.sales_items_map.get(unique_item_id)
        if not item_data:
            print(f"SalesTable: Attempted to update non-existent item: {unique_item_id}")
            return

        try:
            # Find the index of the item in the list to update the correct ft.DataRow
            # This assumes sales_items_data_list order matches datatable.rows order
            idx_in_list = -1
            for i, current_item_data in enumerate(self.sales_items_data_list):
                if current_item_data.unique_id == unique_item_id:
                    idx_in_list = i
                    break
            
            if idx_in_list != -1:
                # Re-create the DataRow for this specific item
                self.datatable.rows[idx_in_list] = item_data.to_datarow()
                print(f"SalesTable: Refreshed row for item {unique_item_id} at index {idx_in_list}")
            else: 
                # This case should be less frequent if list and map are synced,
                # especially with the "move to top" logic rebuilding all rows.
                print(f"SalesTable: Item {unique_item_id} in map but not list during specific update. Rebuilding all rows.")
                self.datatable.rows = [item.to_datarow() for item in self.sales_items_data_list]

        except Exception as e:
            print(f"SalesTable: Error updating specific datarow for {unique_item_id}: {e}. Rebuilding all rows.")
            self.datatable.rows = [item.to_datarow() for item in self.sales_items_data_list]

        if self.page and self.page.controls: self.page.update()


    def get_all_data_items(self) -> List[SalesEntryItemData]:
        return self.sales_items_data_list

    def get_all_items_for_submission(self) -> List[SalesEntryItemData]:
        return [item for item in self.sales_items_data_list if item.is_processed_for_sale or item.all_tickets_sold_confirmed]

    def get_item_by_book_id(self, book_db_id: int) -> Optional[SalesEntryItemData]:
        unique_id = f"book-{book_db_id}"
        return self.sales_items_map.get(unique_id)

```
--- File Separator ---
```python
// Filename: app/ui/components/widgets/function_button.py
from typing import Any, Optional, Dict, Callable # Added Callable
import flet as ft

def create_nav_card_button(
        router: Any,  # Can be your app's Router instance or page for page.go
        text: str,
        icon_name: str, # e.g., ft.icons.HOME_ROUNDED
        accent_color: str, # e.g., ft.colors.BLUE_ACCENT_700
        navigate_to_route: Optional[str] = None, # Made optional
        on_click_override: Optional[Callable[[ft.ControlEvent], None]] = None, # New parameter
        router_params: Optional[Dict[str, Any]] = None,
        icon_size: int = 40,
        border_radius: int = 12,
        background_opacity: float = 0.15,
        shadow_opacity: float = 0.25,
        disabled: bool = False,
        tooltip: Optional[str] = None,
        height: float = 150,
        width: float = 150,
) -> ft.Card:

    effective_router_params = router_params if router_params is not None else {}

    def handle_click(e: ft.ControlEvent):
        if disabled:
            return
        
        if on_click_override:
            on_click_override(e)
        elif navigate_to_route:
            # print(f"NavCard Clicked: Navigating to {navigate_to_route} with params {effective_router_params}")
            if hasattr(router, 'navigate_to'):
                router.navigate_to(navigate_to_route, **effective_router_params)
            elif hasattr(router, 'go'): # For Flet's page.go
                router.go(navigate_to_route)
            else:
                print("Router object not recognized or navigation method missing.")
        else:
            print(f"NavCard '{text}' clicked, but no navigation route or override handler defined.")


    button_internal_content = ft.Column(
        [
            ft.Icon(
                name=icon_name,
                size=icon_size,
                color=ft.Colors.with_opacity(0.9, accent_color) if not disabled else ft.Colors.ON_SURFACE_VARIANT,
            ),
            ft.Container(height=5),
            ft.Text(
                text,
                weight=ft.FontWeight.W_500,
                size=14,
                text_align=ft.TextAlign.CENTER,
                color=ft.Colors.with_opacity(0.85, accent_color) if not disabled else ft.Colors.ON_SURFACE_VARIANT,
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=4,
    )

    clickable_area = ft.Container(
        content=button_internal_content,
        alignment=ft.alignment.center,
        padding=15,
        border_radius=ft.border_radius.all(border_radius),
        ink=not disabled,
        on_click=handle_click if not disabled else None,
        bgcolor=ft.Colors.with_opacity(background_opacity, accent_color) if not disabled else ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE),
        tooltip=tooltip if not disabled else "Disabled",
        height=height,
        width=width,
    )

    return ft.Card(
        content=clickable_area,
        elevation=5 if not disabled else 1,
        shadow_color=ft.Colors.with_opacity(shadow_opacity, accent_color) if not disabled else ft.Colors.BLACK26,
    )

```
--- File Separator ---
```python
// Filename: app/ui/views/admin_dashboard_view.py
import flet as ft
from typing import List, Dict, Tuple, Any

from sqlalchemy.orm import Session

from app.constants import (
    LOGIN_ROUTE, GAME_MANAGEMENT_ROUTE, ADMIN_DASHBOARD_ROUTE, BOOK_MANAGEMENT_ROUTE,
    SALES_ENTRY_ROUTE, BOOK_ACTION_ADD_NEW, BOOK_ACTION_FULL_SALE, BOOK_ACTION_ACTIVATE
)
from app.core.models import User
from app.services import BookService, SalesEntryService, GameService # Import services
from app.data.database import get_db_session # For dialog callbacks
from app.ui.components.widgets.function_button import create_nav_card_button
from app.ui.components.common.appbar_factory import create_appbar
from app.ui.components.dialogs.book_action_dialog import BookActionDialog # New dialog


class AdminDashboardView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user: User, license_status: bool, **params):
        super().__init__(expand=True)
        self.page = page
        self.router = router
        self.current_user = current_user
        self.license_status = license_status

        # Initialize services
        self.book_service = BookService()
        self.sales_entry_service = SalesEntryService()
        self.game_service = GameService() # For BookActionDialog

        self.navigation_params_for_children = {
            "current_user": self.current_user,
            "license_status": self.license_status,
            "previous_view_route": ADMIN_DASHBOARD_ROUTE,
            "previous_view_params": {
                "current_user": self.current_user,
                "license_status": self.license_status,
            },
        }

        self.page.appbar = create_appbar(
            page=self.page,
            router=self.router,
            title_text="Admin Dashboard",
            current_user=self.current_user,
            license_status=self.license_status
        )
        self.content = self._build_body()

    def _create_section_quadrant(self, title: str, title_color: str,
                                 button_row_controls: list, gradient_colors: list) -> ft.Container:
        scrollable_content = ft.Column(
            controls=[
                ft.Text(
                    title,
                    weight=ft.FontWeight.BOLD,
                    size=20,
                    color=title_color,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Row(
                    controls=button_row_controls,
                    spacing=10,
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    wrap=True,
                ),
            ],
            spacing=15,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.ADAPTIVE,
        )
        quadrant_container = ft.Container(
            content=scrollable_content,
            padding=15,
            border_radius=ft.border_radius.all(10),
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=gradient_colors,
            ),
            expand=True,
            alignment=ft.alignment.center,
        )
        return quadrant_container

    # --- Callbacks for BookActionDialog ---
    def _process_full_book_sale_batch(self, db: Session, items_to_process: List[Dict[str, Any]], current_user: User) -> Tuple[int, int, List[str]]:
        success_count = 0
        failure_count = 0
        error_messages: List[str] = []

        for item_data in items_to_process:
            book_number = item_data['book_number_str']
            game_number = item_data['game_number_str']
            game_id = item_data['game_id']
            
            try:
                # Find the book first using game_id and book_number
                book_model = self.book_service.get_book_by_game_and_book_number(db, game_id, book_number)
                if not book_model:
                    raise BookNotFoundError(f"Book {game_number}-{book_number} not found in database.")
                if not book_model.game: # Should be loaded by get_book_by_game_and_book_number or eager loaded
                    db.refresh(book_model, attribute_names=['game'])

                # 1. Mark book as fully sold (updates book status, current_ticket_number)
                self.book_service.mark_book_as_fully_sold(db, book_model.id)
                
                # 2. Create a sales entry for the full book sale
                self.sales_entry_service.create_sales_entry_for_full_book(db, book_model, current_user.id)
                
                success_count += 1
            except Exception as e:
                failure_count += 1
                err_msg = f"Book {game_number}-{book_number}: {str(e)}"
                error_messages.append(err_msg)
                print(f"Error processing full sale for {game_number}-{book_number}: {e}")
        
        return success_count, failure_count, error_messages

    def _process_activate_book_batch(self, db: Session, items_to_process: List[Dict[str, Any]], current_user: User) -> Tuple[int, int, List[str]]:
        success_count = 0
        failure_count = 0
        error_messages: List[str] = []
        book_ids_to_activate = []

        for item_data in items_to_process:
            book_number = item_data['book_number_str']
            game_number = item_data['game_number_str']
            game_id = item_data['game_id']
            try:
                book_model = self.book_service.get_book_by_game_and_book_number(db, game_id, book_number)
                if not book_model:
                    raise BookNotFoundError(f"Book {game_number}-{book_number} not found for activation.")
                book_ids_to_activate.append(book_model.id)
            except Exception as e:
                failure_count +=1
                error_messages.append(f"Book {game_number}-{book_number} pre-check failed: {e}")


        if book_ids_to_activate:
            activated_books, activation_errors = self.book_service.activate_books_batch(db, book_ids_to_activate)
            success_count += len(activated_books)
            failure_count += len(activation_errors)
            error_messages.extend(activation_errors)
            
        return success_count, failure_count, error_messages

    # --- Dialog Openers ---
    def _open_full_book_sale_dialog(self, e: ft.ControlEvent):
        dialog = BookActionDialog(
            page_ref=self.page,
            current_user_ref=self.current_user,
            dialog_title="Process Full Book Sale",
            action_button_text="Mark Books as Sold",
            action_type=BOOK_ACTION_FULL_SALE,
            on_confirm_batch_callback=self._process_full_book_sale_batch,
            game_service=self.game_service,
            require_ticket_scan=False # Only game+book needed to identify for full sale
        )
        dialog.open_dialog()


    def _open_activate_book_dialog(self, e: ft.ControlEvent):
        dialog = BookActionDialog(
            page_ref=self.page,
            current_user_ref=self.current_user, # Not strictly needed by activate callback but good practice
            dialog_title="Activate Books",
            action_button_text="Activate Selected Books",
            action_type=BOOK_ACTION_ACTIVATE,
            on_confirm_batch_callback=self._process_activate_book_batch,
            game_service=self.game_service,
            require_ticket_scan=False
        )
        dialog.open_dialog()


    def _build_sales_functions_quadrant(self) -> ft.Container:
        buttons = [
            create_nav_card_button(
                router=self.router, text="Sales Entry", icon_name=ft.Icons.POINT_OF_SALE_ROUNDED,
                accent_color=ft.Colors.GREEN_700, navigate_to_route=SALES_ENTRY_ROUTE, tooltip="Add Daily Sales",
                router_params=self.navigation_params_for_children),
            create_nav_card_button(
                router=self.router, text="Full Book Sale", icon_name=ft.Icons.BOOK_ONLINE_ROUNDED,
                accent_color=ft.Colors.BLUE_700, tooltip="Mark entire books as sold",
                on_click_override=self._open_full_book_sale_dialog), # Uses on_click_override
            create_nav_card_button(
                router=self.router, text="Activate Book", icon_name=ft.Icons.AUTO_STORIES_ROUNDED,
                accent_color=ft.Colors.TEAL_700, tooltip="Activate specific books for sales",
                on_click_override=self._open_activate_book_dialog), # Uses on_click_override
        ]
        return self._create_section_quadrant(
            title="Sale Functions", title_color=ft.Colors.CYAN_900,
            button_row_controls=buttons,
            gradient_colors=[ft.Colors.CYAN_50, ft.Colors.LIGHT_BLUE_100]
        )

    def _build_inventory_functions_quadrant(self) -> ft.Container:
        buttons = [
            create_nav_card_button(
                router=self.router, text="Manage Games", icon_name=ft.Icons.SPORTS_ESPORTS_ROUNDED,
                accent_color=ft.Colors.DEEP_PURPLE_600, navigate_to_route=GAME_MANAGEMENT_ROUTE,
                tooltip="View, edit, or add game types", router_params=self.navigation_params_for_children,
            ),
            create_nav_card_button(
                router=self.router, text="Manage Books", icon_name=ft.Icons.MENU_BOOK_ROUNDED,
                accent_color=ft.Colors.BROWN_600, navigate_to_route=BOOK_MANAGEMENT_ROUTE,
                tooltip="View, edit, or add lottery ticket books", router_params=self.navigation_params_for_children,
            ),
        ]
        return self._create_section_quadrant(
            title="Inventory Control", title_color=ft.Colors.GREEN_800,
            button_row_controls=buttons,
            gradient_colors=[ft.Colors.GREEN_100, ft.Colors.LIGHT_GREEN_200]
        )

    def _build_report_functions_quadrant(self) -> ft.Container:
        buttons = [
            create_nav_card_button(
                router=self.router, text="Sales by Date", icon_name=ft.Icons.CALENDAR_MONTH_ROUNDED,
                accent_color=ft.Colors.ORANGE_700, navigate_to_route=LOGIN_ROUTE, tooltip="Sales Report", disabled=True),
            create_nav_card_button(
                router=self.router, text="Book Open Report", icon_name=ft.Icons.ASSESSMENT_ROUNDED,
                accent_color=ft.Colors.INDIGO_400, navigate_to_route=LOGIN_ROUTE, tooltip="Book Open Report", disabled=True),
            create_nav_card_button(
                router=self.router, text="Game Expiry Report", icon_name=ft.Icons.UPDATE_ROUNDED,
                accent_color=ft.Colors.DEEP_ORANGE_700, navigate_to_route=LOGIN_ROUTE, tooltip="Game Expire Report", disabled=True),
            create_nav_card_button(
                router=self.router, text="Stock Levels", icon_name=ft.Icons.STACKED_BAR_CHART_ROUNDED,
                accent_color=ft.Colors.BROWN_500, navigate_to_route=LOGIN_ROUTE, tooltip="Book Stock Report", disabled=True),
        ]
        return self._create_section_quadrant(
            title="Data & Reports", title_color=ft.Colors.AMBER_900,
            button_row_controls=buttons,
            gradient_colors=[ft.Colors.AMBER_50, ft.Colors.YELLOW_100]
        )

    def _build_management_functions_quadrant(self) -> ft.Container:
        buttons = [
            create_nav_card_button(
                router=self.router, text="Manage Users", icon_name=ft.Icons.MANAGE_ACCOUNTS_ROUNDED,
                accent_color=ft.Colors.INDIGO_700, navigate_to_route=LOGIN_ROUTE, tooltip="Manage Users", disabled=True),
            create_nav_card_button(
                router=self.router, text="Backup Database", icon_name=ft.Icons.SETTINGS_BACKUP_RESTORE_ROUNDED,
                accent_color=ft.Colors.BLUE_800, navigate_to_route=LOGIN_ROUTE, tooltip="Backup Database", disabled=True),
        ]
        return self._create_section_quadrant(
            title="System Management", title_color=ft.Colors.DEEP_PURPLE_800,
            button_row_controls=buttons,
            gradient_colors=[ft.Colors.DEEP_PURPLE_50, ft.Colors.INDIGO_100]
        )

    def _build_body(self) -> ft.Column:
        divider_color = ft.Colors.with_opacity(0.3, ft.Colors.ON_SURFACE)
        divider_thickness = 2
        row1 = ft.Row(
            controls=[
                self._build_sales_functions_quadrant(),
                self._build_inventory_functions_quadrant(),
            ],
            spacing=10, expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH
        )
        row2 = ft.Row(
            controls=[
                self._build_report_functions_quadrant(),
                self._build_management_functions_quadrant(),
            ],
            spacing=10, expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH
        )
        return ft.Column(
            controls=[row1, ft.Divider(height=divider_thickness, thickness=divider_thickness, color=divider_color), row2],
            spacing=10, expand=True,
        )

```
--- File Separator ---
```python
// Filename: app/ui/views/admin/book_management.py
import flet as ft
from typing import List, Optional, Callable, Dict, Tuple, Any

from sqlalchemy.orm import Session # For type hinting callback

from app.constants import ADMIN_DASHBOARD_ROUTE, BOOK_ACTION_ADD_NEW
from app.core.models import User
from app.services.book_service import BookService
from app.services.game_service import GameService
from app.ui.components.common.appbar_factory import create_appbar
from app.ui.components.common.search_bar_component import SearchBarComponent
from app.ui.components.tables.books_table import BooksTable
from app.ui.components.dialogs.book_action_dialog import BookActionDialog # New generic dialog

class BookManagementView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user: User, license_status: bool,
                 previous_view_route: str = ADMIN_DASHBOARD_ROUTE,
                 previous_view_params: dict = None, **params):
        super().__init__(expand=True, padding=0)
        self.page = page
        self.router = router
        self.current_user = current_user
        self.license_status = license_status
        self.previous_view_route = previous_view_route
        self.previous_view_params = previous_view_params if previous_view_params is not None else {}

        self.book_service = BookService()
        self.game_service = GameService() # Needed for BookActionDialog

        self.total_books_widget = ft.Text("", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD)
        self.active_books_widget = ft.Text("", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)
        self.inactive_books_widget = ft.Text("", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_700)

        self.books_table_component = BooksTable(
            page=self.page,
            book_service=self.book_service,
            on_data_changed_stats=self._handle_table_data_stats_change
        )
        self.search_bar = SearchBarComponent(
            on_search_changed=self._on_search_term_changed,
            label="Search Books (Game No., Book No., Game Name)"
        )

        self.page.appbar = create_appbar(
            page=self.page, router=self.router, title_text=f"{self.current_user.role.capitalize()} Book Management",
            current_user=self.current_user, license_status=self.license_status,
            leading_widget=ft.IconButton(ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED, tooltip="Go Back", icon_color=ft.Colors.WHITE, on_click=self._go_back)
        )
        self.content = self._build_body()
        self.books_table_component.refresh_data_and_ui()

    def _go_back(self, e):
        nav_params = {**self.previous_view_params}
        if "current_user" not in nav_params and self.current_user: nav_params["current_user"] = self.current_user
        if "license_status" not in nav_params and self.license_status is not None: nav_params["license_status"] = self.license_status
        self.router.navigate_to(self.previous_view_route, **nav_params)

    def _on_search_term_changed(self, search_term: str):
        self.books_table_component.refresh_data_and_ui(search_term=search_term)

    def _handle_table_data_stats_change(self, total: int, active: int, inactive: int):
        self.total_books_widget.value = f"Total Books: {total}"
        self.active_books_widget.value = f"Active: {active}"
        self.inactive_books_widget.value = f"Inactive: {inactive}"
        if self.page and self.page.controls: self.page.update()

    def _build_body(self) -> ft.Container:
        stats_row = ft.Row(
            [self.total_books_widget, ft.VerticalDivider(), self.active_books_widget, ft.VerticalDivider(), self.inactive_books_widget],
            alignment=ft.MainAxisAlignment.START, spacing=15
        )
        actions_row = ft.Row(
            [
                self.search_bar,
                ft.FilledButton("Add New Books", icon=ft.Icons.LIBRARY_ADD_ROUNDED, on_click=self._open_add_books_dialog_handler, height=48)
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=15
        )
        card_content = ft.Column(
            [
                ft.Text("Book Inventory & Management", style=ft.TextThemeStyle.HEADLINE_SMALL, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.LEFT),
                ft.Divider(height=10), stats_row, ft.Divider(height=20), actions_row,
                ft.Divider(height=15, color=ft.Colors.TRANSPARENT), self.books_table_component,
            ], spacing=15, expand=True
        )
        TARGET_CARD_MAX_WIDTH = 1100; MIN_CARD_WIDTH = 360; SIDE_PADDING = 20
        page_width_available = self.page.width if self.page.width and self.page.width > (2 * SIDE_PADDING) else (MIN_CARD_WIDTH + 2 * SIDE_PADDING)
        card_effective_width = min(TARGET_CARD_MAX_WIDTH, page_width_available - (2 * SIDE_PADDING))
        card_effective_width = max(MIN_CARD_WIDTH, card_effective_width)
        if page_width_available <= (2 * SIDE_PADDING): card_effective_width = max(10, page_width_available - 2)
        elif card_effective_width <= 0: card_effective_width = MIN_CARD_WIDTH

        main_card = ft.Card(
            content=ft.Container(content=card_content, padding=20, border_radius=ft.border_radius.all(10)),
            elevation=2, width=card_effective_width
        )
        return ft.Container(content=main_card, alignment=ft.alignment.top_center, padding=20, expand=True)

    def _process_add_new_books_batch(self, db: Session, items_to_process: List[Dict[str, Any]], current_user: User) -> Tuple[int, int, List[str]]:
        """
        Callback for BookActionDialog to add new books.
        items_to_process contains dicts from TempBookActionItem.to_submission_dict()
        """
        books_for_service_call = []
        for item_data in items_to_process:
            books_for_service_call.append({
                "game_id": item_data['game_id'],
                "book_number_str": item_data['book_number_str'],
                "game_number_str": item_data['game_number_str'] # For error messages if any
            })
        
        created_books, service_errors = self.book_service.add_books_in_batch(db, books_for_service_call)
        
        success_count = len(created_books)
        failure_count = len(service_errors)
        
        # After batch processing, refresh the main books table in this view
        self.books_table_component.refresh_data_and_ui(self.search_bar.get_value())
        
        return success_count, failure_count, service_errors


    def _open_add_books_dialog_handler(self, e: ft.ControlEvent):
        add_books_dialog = BookActionDialog(
            page_ref=self.page,
            current_user_ref=self.current_user, # Pass current user for the callback
            dialog_title="Add New Books to Inventory",
            action_button_text="Confirm & Add Books",
            action_type=BOOK_ACTION_ADD_NEW,
            on_confirm_batch_callback=self._process_add_new_books_batch,
            game_service=self.game_service,
            require_ticket_scan=False # For adding books, ticket number is not scanned
        )
        add_books_dialog.open_dialog()

```
--- File Separator ---
```python
// Filename: app/ui/views/admin/sales_entry_view.py
import flet as ft
import datetime
from typing import List, Optional, Dict, Any

from app.constants import ADMIN_DASHBOARD_ROUTE, MIN_REQUIRED_SCAN_LENGTH_WITH_TICKET
from app.core.models import User, Book as BookModel
from app.services.sales_entry_service import SalesEntryService
from app.data.database import get_db_session
from app.core.exceptions import ValidationError, DatabaseError, GameNotFoundError, BookNotFoundError

from app.ui.components.common.appbar_factory import create_appbar
from app.ui.components.common.dialog_factory import create_confirmation_dialog
from app.ui.components.tables.sales_entry_items_table import SalesEntryItemsTable
from app.ui.components.tables.sales_entry_item_data import SalesEntryItemData
from app.ui.components.common.scan_input_handler import ScanInputHandler # New Handler


class SalesEntryView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user: User, license_status: bool,
                 previous_view_route: str = ADMIN_DASHBOARD_ROUTE,
                 previous_view_params: dict = None, **params):
        super().__init__(expand=True, padding=0)
        self.page = page
        self.router = router
        self.current_user = current_user
        self.license_status = license_status
        self.previous_view_route = previous_view_route
        self.previous_view_params = previous_view_params if previous_view_params is not None else {}

        self.sales_entry_service = SalesEntryService()

        self.today_date_widget = ft.Text(
            f"Date: {datetime.datetime.now().strftime('%A, %B %d, %Y %I:%M %p')}",
            style=ft.TextThemeStyle.TITLE_MEDIUM,
            weight=ft.FontWeight.BOLD
        )
        self.books_in_table_count_widget = ft.Text(
            "Books In Table: 0", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.NORMAL
        )
        self.pending_entry_books_count_widget = ft.Text(
            "Pending Entry: 0", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.NORMAL, color=ft.Colors.ORANGE_ACCENT_700
        )
        
        self.scanner_text_field: ft.TextField = ft.TextField( # Initialize TextField here
            label="Scan Full Book Code (e.g., GameNo+BookNo+TicketNo)",
            hint_text=f"Input Game, Book, Ticket numbers for {MIN_REQUIRED_SCAN_LENGTH_WITH_TICKET} chars total.",
            autofocus=True, border_radius=8, prefix_icon=ft.Icons.QR_CODE_SCANNER_ROUNDED,
            expand=True, height=50
        )
        self.scan_input_handler: Optional[ScanInputHandler] = None # Will be initialized in _build_body or after
        
        self.sales_items_table_component: Optional[SalesEntryItemsTable] = None # Init in _build_body
        self.grand_total_sales_widget = ft.Text("Grand Total Sales: $0", weight=ft.FontWeight.BOLD, size=16)
        self.total_tickets_sold_widget = ft.Text("Total Tickets Sold: 0", weight=ft.FontWeight.BOLD, size=16)
        self.scan_error_text_widget = ft.Text("", color=ft.Colors.RED_ACCENT_700, visible=False, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)

        self.page.appbar = create_appbar(
            page=self.page, router=self.router, title_text=f"{self.current_user.role.capitalize()} > Sales Entry",
            current_user=self.current_user, license_status=self.license_status,
            leading_widget=ft.IconButton(
                icon=ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                tooltip="Go Back to Admin Dashboard",
                icon_color=ft.Colors.WHITE,
                on_click=self._go_back
            )
        )
        self.content = self._build_body() # Builds UI, including initializing ScanInputHandler
        self._load_initial_data_for_table()

    def _go_back(self, e):
        nav_params = {**self.previous_view_params}
        if "current_user" not in nav_params and self.current_user: nav_params["current_user"] = self.current_user
        if "license_status" not in nav_params and self.license_status is not None: nav_params["license_status"] = self.license_status
        self.router.navigate_to(self.previous_view_route, **nav_params)

    def _load_initial_data_for_table(self):
        if self.sales_items_table_component:
            self.sales_items_table_component.load_initial_active_books()

    def _handle_table_items_loaded(self, all_items: List[SalesEntryItemData]):
        self._update_totals_and_book_counts(None) # Pass None or all_items

    def _on_scan_complete_callback(self, parsed_data: Dict[str, str]):
        """Callback for ScanInputHandler on successful scan and parse."""
        self._clear_scan_error() # Clear previous errors
        game_no_str = parsed_data.get('game_no', '')
        book_no_str = parsed_data.get('book_no', '')
        ticket_no_str = parsed_data.get('ticket_no', '') # ticket_no is expected here
        
        self._process_scan_and_update_table(game_no_str, book_no_str, ticket_no_str)
        # ScanInputHandler will auto-clear and auto-focus by default

    def _on_scan_error_callback(self, error_message: str):
        """Callback for ScanInputHandler on scan/parse error."""
        self.scan_error_text_widget.value = error_message
        self.scan_error_text_widget.visible = True
        if self.scan_error_text_widget.page: self.scan_error_text_widget.update()
        if self.page: self.page.update()
        if self.scan_input_handler: self.scan_input_handler.focus_input()


    def _clear_scan_error(self):
        self.scan_error_text_widget.value = ""
        self.scan_error_text_widget.visible = False
        if self.scan_error_text_widget.page : self.scan_error_text_widget.update()


    def _process_scan_and_update_table(self, game_no_str: str, book_no_str: str, ticket_no_str: str):
        self._clear_scan_error()
        item_data_processed: Optional[SalesEntryItemData] = None
        try:
            # Validation is largely handled by ScanInputHandler, but can double-check here if needed
            # For example, specific business rules not covered by generic parsing.

            with get_db_session() as db:
                book_model_instance = self.sales_entry_service.get_or_create_book_for_sale(db, game_no_str, book_no_str)
            
            if self.sales_items_table_component:
                item_data_processed = self.sales_items_table_component.add_or_update_book_for_sale(book_model_instance, ticket_no_str)
            else: 
                raise Exception("Sales items table component not initialized.")

        except (ValidationError, GameNotFoundError, BookNotFoundError, DatabaseError) as e:
            self._on_scan_error_callback(str(e.message if hasattr(e, 'message') else e))
        except Exception as ex_general:
            self._on_scan_error_callback(f"Error processing scan: {type(ex_general).__name__} - {ex_general}")
        
        if self.page and self.page.controls: self.page.update() # Ensure UI reflects changes
        
        # Focus logic: if item processed, focus its text field; otherwise, focus scanner.
        if item_data_processed and item_data_processed.ui_new_ticket_no_ref:
            if item_data_processed.ui_new_ticket_no_ref.page:
                item_data_processed.ui_new_ticket_no_ref.focus()
        elif self.scan_input_handler:
            self.scan_input_handler.focus_input()


    def _update_totals_and_book_counts(self, changed_item_data: Optional[SalesEntryItemData] = None):
        if not self.sales_items_table_component: return

        all_display_items = self.sales_items_table_component.get_all_data_items()
        grand_total_sales_val = sum(item.amount_calculated for item in all_display_items if item.is_processed_for_sale or item.all_tickets_sold_confirmed)
        total_tickets_sold_val = sum(item.tickets_sold_calculated for item in all_display_items if item.is_processed_for_sale or item.all_tickets_sold_confirmed)
        pending_entry_count = sum(1 for item in all_display_items if not item.ui_new_ticket_no_str.strip() and not item.all_tickets_sold_confirmed)

        self.grand_total_sales_widget.value = f"Grand Total Sales: ${grand_total_sales_val}"
        self.total_tickets_sold_widget.value = f"Total Tickets Sold: {total_tickets_sold_val}"
        self.books_in_table_count_widget.value = f"Books In Table: {len(all_display_items)}"
        self.pending_entry_books_count_widget.value = f"Pending Entry: {pending_entry_count}"

        if self.grand_total_sales_widget.page: self.grand_total_sales_widget.update()
        if self.total_tickets_sold_widget.page: self.total_tickets_sold_widget.update()
        if self.books_in_table_count_widget.page: self.books_in_table_count_widget.update()
        if self.pending_entry_books_count_widget.page: self.pending_entry_books_count_widget.update()

    def _handle_submit_all_sales_click(self, e):
        if not self.sales_items_table_component:
            self.page.open(ft.SnackBar(ft.Text("Sales table not ready."), open=True, bgcolor=ft.Colors.ERROR))
            return
        all_current_table_items = self.sales_items_table_component.get_all_data_items()
        if not all_current_table_items:
            self.page.open(ft.SnackBar(ft.Text("No books loaded in the sales table."), open=True))
            return
        items_with_empty_fields: List[SalesEntryItemData] = []
        for item_data in all_current_table_items:
            if not item_data.ui_new_ticket_no_str.strip() and not item_data.all_tickets_sold_confirmed:
                items_with_empty_fields.append(item_data)
        if items_with_empty_fields:
            self._prompt_for_empty_field_books_confirmation(items_with_empty_fields)
        else:
            self._confirm_final_submission()

    def _prompt_for_empty_field_books_confirmation(self, items_to_confirm: List[SalesEntryItemData]):
        book_details_str = "\n".join([f"- Game {item.book_model.game.game_number} / Book {item.book_number} / {item.game_name} / ${item.game_price}" for item in items_to_confirm])
        dialog_content_column = ft.Column(
            [
                ft.Text("The following books have no new ticket number entered:", weight=ft.FontWeight.BOLD),
                ft.Container(ft.Column(controls=[ft.Text(book_details_str, selectable=True)], scroll=ft.ScrollMode.ADAPTIVE), height=min(150, len(items_to_confirm)*25), padding=5),
                ft.Divider(height=10), ft.Text("Do you want to mark them as ALL TICKETS SOLD?"),
                ft.Text("Choosing 'No' will skip these specific books from this submission if their ticket number remains empty.", size=11, italic=True, color=ft.Colors.OUTLINE)
            ], tight=True, spacing=10, width=450
        )
        def _handle_dialog_choice(mark_as_all_sold: bool):
            self.page.close(self.page.dialog)
            if mark_as_all_sold:
                for item_data in items_to_confirm:
                    item_data.confirm_all_sold() # This calls item's on_change, which calls _update_totals_and_book_counts
                    if self.sales_items_table_component: # And also explicitly refresh row in table
                        self.sales_items_table_component.update_datarow_for_item(item_data.unique_id)
            # Ensure totals are up-to-date before final submission prompt
            self._update_totals_and_book_counts() 
            self._confirm_final_submission()

        confirm_dialog = ft.AlertDialog(
            modal=True, title=ft.Text("Confirm Unentered Books"), content=dialog_content_column,
            actions=[
                ft.TextButton("Cancel Submission", on_click=lambda _: self.page.close(self.page.dialog)),
                ft.TextButton("No, Skip These Empty", on_click=lambda _: _handle_dialog_choice(False)),
                ft.FilledButton("Yes, Mark All Sold", on_click=lambda _: _handle_dialog_choice(True)),
            ], actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = confirm_dialog
        self.page.open(confirm_dialog)

    def _confirm_final_submission(self):
        if not self.sales_items_table_component: return
        items_ready_for_db = self.sales_items_table_component.get_all_items_for_submission()
        if not items_ready_for_db:
            self.page.open(ft.SnackBar(ft.Text("No entries are ready for submission."), open=True, duration=5000))
            return
        
        total_sales_val = sum(item.amount_calculated for item in items_ready_for_db)
        total_tickets_val = sum(item.tickets_sold_calculated for item in items_ready_for_db)

        confirmation_content = ft.Column([
            ft.Text(f"You are about to submit {len(items_ready_for_db)} sales entries."),
            ft.Text(f"Total Tickets in this submission: {total_tickets_val}"),
            ft.Text(f"Total Sales Amount in this submission: ${total_sales_val}"),
            ft.Divider(height=10),
            ft.Text("This action CANNOT be easily reverted. Proceed?", weight=ft.FontWeight.BOLD)
        ])
        
        final_confirm_dialog = create_confirmation_dialog(
            title_text="Confirm Sales Submission",
            content_control=confirmation_content,
            on_confirm=self._execute_database_submission,
            on_cancel=lambda ev: self.page.close(self.page.dialog),
            confirm_button_text="Save Sales",
            confirm_button_style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_ACCENT_700, color=ft.Colors.WHITE)
        )
        self.page.dialog = final_confirm_dialog
        self.page.open(final_confirm_dialog)

    def _execute_database_submission(self, e):
        self.page.close(self.page.dialog)
        if not self.sales_items_table_component or not self.current_user or self.current_user.id is None:
            self.page.open(ft.SnackBar(ft.Text("Critical error: Table or user session invalid."), open=True, bgcolor=ft.Colors.ERROR))
            return
        items_payload_for_service = [item.get_data_for_submission() for item in self.sales_items_table_component.get_all_items_for_submission()]
        if not items_payload_for_service:
            self.page.open(ft.SnackBar(ft.Text("No valid sales data to submit after final confirmations."), open=True))
            return
        try:
            with get_db_session() as db:
                sales_saved, books_updated, errors = self.sales_entry_service.process_and_save_sales_batch(
                    db, self.current_user.id, items_payload_for_service
                )
            result_message = f"{sales_saved} sales entries saved. {books_updated} books updated."
            if errors:
                result_message += f"\nEncountered {len(errors)} issues (see console log)."
                print("Sales Submission Errors:", errors)
                self.page.open(ft.SnackBar(
                    content=ft.Column([ft.Text(result_message), ft.Text("Some items had errors. Check console logs.", selectable=True)]),
                    open=True, bgcolor=ft.Colors.AMBER_ACCENT_700, duration=15000
                ))
            else:
                self.page.open(ft.SnackBar(ft.Text(result_message), open=True, bgcolor=ft.Colors.GREEN))
            
            self._load_initial_data_for_table() # Reload table with fresh data
            # _update_totals_and_book_counts is called by _handle_table_items_loaded
            self._go_back(e) # Navigate back after submission
        except Exception as ex_submit:
            error_detail = f"{type(ex_submit).__name__}: {ex_submit}"
            self.page.open(ft.SnackBar(ft.Text(f"Failed to submit sales: {error_detail}"), open=True, bgcolor=ft.Colors.ERROR, duration=10000))
            print(f"Sales submission execution error: {error_detail}")

    def _build_body(self) -> ft.Container:
        # Initialize ScanInputHandler with the TextField
        self.scan_input_handler = ScanInputHandler(
            scan_text_field=self.scanner_text_field,
            on_scan_complete=self._on_scan_complete_callback,
            on_scan_error=self._on_scan_error_callback,
            require_ticket=True # Sales entry requires game+book+ticket
        )
        
        self.sales_items_table_component = SalesEntryItemsTable(
            page_ref=self.page, sales_entry_service=self.sales_entry_service,
            on_item_change_callback=self._update_totals_and_book_counts, # Single item changed
            on_all_items_loaded_callback=self._handle_table_items_loaded # All initial items loaded
        )

        info_row = ft.Row(
            [
                self.today_date_widget,
                ft.Container(expand=True),
                self.books_in_table_count_widget,
                ft.VerticalDivider(width=1, color=ft.Colors.with_opacity(0.3, ft.Colors.ON_SURFACE), thickness=1),
                self.pending_entry_books_count_widget,
            ],
            alignment=ft.MainAxisAlignment.START, spacing=15, vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
        top_section = ft.Column(
            [info_row,
             ft.Row([self.scanner_text_field], vertical_alignment=ft.CrossAxisAlignment.CENTER), # Use the class member
             self.scan_error_text_widget], spacing=10
        )
        bottom_summary_section = ft.Container(
            ft.Row(
                [self.total_tickets_sold_widget, self.grand_total_sales_widget,
                 ft.FilledButton(
                     "Submit All Sales", icon=ft.Icons.SAVE_AS_ROUNDED,
                     on_click=self._handle_submit_all_sales_click,
                     style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE, shape=ft.RoundedRectangleBorder(radius=8)),
                     height=45, tooltip="Finalize and save all entered sales data for loaded books."
                 )],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER
            ), padding=ft.padding.symmetric(vertical=15, horizontal=5)
        )
        sales_card_content = ft.Column(
            [top_section, ft.Divider(height=15), self.sales_items_table_component,
             ft.Divider(height=15), bottom_summary_section], spacing=12, expand=True
        )
        TARGET_CARD_MAX_WIDTH = 1200
        page_width_for_calc = self.page.width if self.page.width and self.page.width > 0 else TARGET_CARD_MAX_WIDTH + 40
        card_effective_width = min(TARGET_CARD_MAX_WIDTH, page_width_for_calc - 40)
        card_effective_width = max(card_effective_width, 750)
        sales_card = ft.Card(
            content=ft.Container(
                content=sales_card_content,
                padding=ft.padding.symmetric(vertical=15, horizontal=20),
                border_radius=ft.border_radius.all(10)
            ), elevation=3, width=card_effective_width,
        )
        return ft.Container(content=sales_card, alignment=ft.alignment.top_center, padding=ft.padding.all(15), expand=True)

```
--- END OF CHANGED FILES ---