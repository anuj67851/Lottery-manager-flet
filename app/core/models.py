"""
Defines the SQLAlchemy models for the application.

This module contains the database schema definitions using SQLAlchemy's
declarative base. It includes the `User`, `Game`, `Book`,
`SalesEntry`, and `ShiftSubmission` models.
"""
import logging

import bcrypt
import datetime
from sqlalchemy import String, Integer, Column, ForeignKey, Boolean, DateTime, UniqueConstraint, Date, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from app.constants import REVERSE_TICKET_ORDER

logger = logging.getLogger(__name__)
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

    # Relationship to ShiftSubmission
    shifts = relationship("ShiftSubmission", back_populates="user", order_by="ShiftSubmission.submission_datetime.desc()")

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

class ShiftSubmission(Base):
    __tablename__ = "shifts" # Using "shifts" for the table name as per ForeignKey in SalesEntry

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    submission_datetime = Column(DateTime, nullable=False, default=datetime.datetime.now, index=True)
    calendar_date = Column(Date, nullable=False, index=True) # Derived at creation

    # User-Reported Cumulative Daily Values (stored as cents)
    reported_total_online_sales_today = Column(Integer, nullable=False) # cents
    reported_total_online_payouts_today = Column(Integer, nullable=False) # cents
    reported_total_instant_payouts_today = Column(Integer, nullable=False) # cents

    # Calculated Delta Values (stored as cents)
    calculated_delta_online_sales = Column(Integer, nullable=False) # cents
    calculated_delta_online_payouts = Column(Integer, nullable=False) # cents
    calculated_delta_instant_payouts = Column(Integer, nullable=False) # cents

    # Instant Sales Aggregates (from SalesEntry records linked to THIS shift)
    total_tickets_sold_instant = Column(Integer, nullable=False, default=0) # count
    total_value_instant = Column(Integer, nullable=False, default=0) # NOW IN CENTS

    # Calculated Drawer Value for THIS Shift Submission (stored as cents)
    calculated_drawer_value = Column(Integer, nullable=False, default=0) # cents

    # Drawer Difference (stored as cents)
    # Positive: actual cash is less than expected (shortfall)
    # Negative: actual cash is more than expected (overage)
    drawer_difference = Column(Integer, nullable=False, default=0) # cents

    created_date = Column(DateTime, nullable=False, default=datetime.datetime.now)

    # Relationships
    user = relationship("User", back_populates="shifts")
    sales_entries = relationship("SalesEntry", back_populates="shift", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if 'submission_datetime' in kwargs and isinstance(kwargs['submission_datetime'], datetime.datetime):
            self.calendar_date = kwargs['submission_datetime'].date()
        elif 'submission_datetime' not in kwargs: # If default is used
            self.calendar_date = datetime.datetime.now().date()


    def __repr__(self):
        return (f"<ShiftSubmission(id={self.id}, user_id={self.user_id}, "
                f"submission_datetime='{self.submission_datetime.strftime('%Y-%m-%d %H:%M:%S') if self.submission_datetime else 'N/A'}', "
                f"calendar_date='{self.calendar_date.strftime('%Y-%m-%d') if self.calendar_date else 'N/A'}', "
                f"total_value_instant_cents={self.total_value_instant}, " # Reflect unit change
                f"calculated_drawer_value_cents={self.calculated_drawer_value}, drawer_difference_cents={self.drawer_difference})>")

class Game(Base):
    """
    Represents a game in the system.
    """
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False, unique=False)
    price = Column(Integer, nullable=False) # Stored as CENTS (e.g., $1.00 is 100)
    total_tickets = Column(Integer, nullable=False)
    is_expired = Column(Boolean, nullable=False, default=False)
    default_ticket_order = Column(String, nullable=False, default=REVERSE_TICKET_ORDER)
    created_date = Column(DateTime, nullable=False, default=datetime.datetime.now)
    expired_date = Column(DateTime, nullable=True)

    books = relationship("Book", back_populates="game")
    game_number = Column(Integer, nullable=False, unique=True)

    @property
    def calculated_total_value(self) -> int: # Returns CENTS
        return (self.price * self.total_tickets) if self.price is not None and self.total_tickets is not None else 0

    def __repr__(self):
        return (f"<Game(id={self.id}, name='{self.name}', price_cents={self.price}, total_tickets={self.total_tickets}, "
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

    # Update Book model to correctly back_populate sales_entries from SalesEntry model
    sales_entries = relationship("SalesEntry", back_populates="book") # This will be adjusted

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
            logger.warning(f"Warning: Cannot set book {self.id} as fully sold. Game association missing.")
            return

        if self.ticket_order == REVERSE_TICKET_ORDER:
            self.current_ticket_number = -1 # State after selling ticket 0
        else: # FORWARD_TICKET_ORDER
            self.current_ticket_number = self.game.total_tickets # State after selling ticket N-1
        self.is_active = False
        if not self.finish_date: # Only set finish_date if not already finished
            self.finish_date = datetime.datetime.now()

    @property
    def remaining_tickets(self) -> int:
        """Calculates the number of tickets remaining in the book."""
        if not self.game or self.game.total_tickets == 0:
            return 0

        if self.ticket_order == REVERSE_TICKET_ORDER:
            # current_ticket_number is the index of the highest ticket still available.
            # If -1, all sold (ticket 0 was last one).
            if self.current_ticket_number == -1:
                return 0
            else:
                # Tickets from current_ticket_number down to 0 are available.
                # e.g., if total=100, initial current=99. If current=99, tickets 0-99 available (100 tickets).
                # If current=0, ticket 0 is available (1 ticket).
                return self.current_ticket_number + 1
        else: # FORWARD_TICKET_ORDER
            # current_ticket_number is the index of the next ticket to be sold.
            # If total_tickets, all sold (ticket N-1 was last one).
            if self.current_ticket_number == self.game.total_tickets:
                return 0
            else:
                # Tickets from current_ticket_number up to total_tickets-1 are available.
                # e.g., if total=100, initial current=0. Tickets 0 to 99 are available.
                # Number of tickets = total_tickets - current_ticket_number.
                return self.game.total_tickets - self.current_ticket_number

    @property
    def remaining_value(self) -> int: # Returns CENTS
        """Calculates the monetary value of the remaining tickets in the book."""
        if not self.game:
            return 0
        # self.game.price is now in CENTS, so remaining_value will also be in CENTS.
        return self.remaining_tickets * self.game.price

    def __repr__(self):
        return (f"<Book(id={self.id}, game_id={self.game_id}, book_number='{self.book_number}', "
                f"ticket_order='{self.ticket_order}', is_active={self.is_active}, current_ticket_number={self.current_ticket_number})>")


class SalesEntry(Base):
    """
    Represents a sales entry for a book instance.
    Now linked to a ShiftSubmission instead of directly to a User.
    """
    __tablename__ = "sales_entries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    start_number = Column(Integer, nullable=False) # Book's current_ticket_number BEFORE this sale
    end_number = Column(Integer, nullable=False)   # Book's current_ticket_number AFTER this sale
    date = Column(DateTime, nullable=False, default=datetime.datetime.now)
    count = Column(Integer, nullable=False) # Calculated
    price = Column(Integer, nullable=False) # Calculated (total for this entry, in CENTS)

    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    book = relationship("Book", back_populates="sales_entries") # Relationship in Book model updated below

    # Changed from user_id to shift_id
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=False, index=True)
    shift = relationship("ShiftSubmission", back_populates="sales_entries")


    def calculate_count_and_price(self):
        """
        Calculates and sets the 'count' and 'price' for this sales entry.
        Assumes self.book and self.book.game are populated.
        `start_number` is the book's state *before* this sale.
        `end_number` is the book's state *after* this sale.
        Price is in CENTS because game.price is in CENTS.
        """
        if self.book and self.book.game:
            if self.book.ticket_order == REVERSE_TICKET_ORDER:
                if self.start_number < self.end_number: # Error condition for reverse
                    self.count = 0
                else:
                    self.count = self.start_number - self.end_number
            else: # FORWARD_TICKET_ORDER
                if self.end_number < self.start_number: # Error condition for forward
                    self.count = 0
                else:
                    self.count = self.end_number - self.start_number

            # self.book.game.price is in CENTS, so self.price will be in CENTS.
            self.price = self.count * self.book.game.price
        else:
            self.count = 0
            self.price = 0

    def __repr__(self):
        return (f"<SalesEntry(id={self.id}, book_id={self.book_id}, shift_id={self.shift_id}, "
                f"start_number={self.start_number}, end_number={self.end_number}, "
                f"date={self.date}, count={self.count}, price_cents={self.price})>") # Updated __repr__


class Configuration(Base):
    __tablename__ = "configurations"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name =  Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    def get_value(self): return self.value
    def set_value(self, value): self.value = value
    def __repr__(self): return f"<Configuration(id={self.id}, name='{self.name}', value='{self.value}')>"