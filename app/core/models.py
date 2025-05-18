"""
Defines the SQLAlchemy models for the application.

This module contains the database schema definitions using SQLAlchemy's
declarative base. It includes the `User`, `Game`, `Book`,
and `SalesEntry` models.
"""
import bcrypt
import datetime # Ensure datetime is imported
from sqlalchemy import String, Integer, Column, ForeignKey, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from app.constants import REVERSE_TICKET_ORDER

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
    created_date = Column(DateTime, nullable=False, default=datetime.datetime.now())
    is_active = Column(Boolean, nullable=False, default=True)

    def set_password(self, plain_password: str):
        """
        Hashes the plain password using bcrypt and stores it.

        Args:
            plain_password (str): The plain text password to hash.
        """
        password_bytes = plain_password.encode('utf-8')
        salt = bcrypt.gensalt()
        self.password = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

    def check_password(self, plain_password: str) -> bool:
        """
        Verifies a plain password against the stored hashed password.

        Args:
            plain_password (str): The plain text password to verify.

        Returns:
            bool: True if the password matches, False otherwise.
        """
        if not self.password:
            return False
        password_bytes = plain_password.encode('utf-8')
        hashed_password_bytes = self.password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_password_bytes)

    def __repr__(self):
        """
        Returns a string representation of the User object.
        """
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"

class Game(Base):
    """
    Represents a game in the system.

    Attributes:
        id (int): The primary key for the game.
        name (str): The unique name of the game.
        price (int): The price of one ticket for the game.
        total_tickets (int): The total number of tickets available for this game type.
        books (relationship): A list of book associated with this game.
        series_number (int, optional): An optional series number for the game.
        default_ticket_order (str, optional): The default order of tickets (e.g., "reverse", "forward").
    """
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False, unique=False)
    price = Column(Integer, nullable=False)
    total_tickets = Column(Integer, nullable=False)
    is_expired = Column(Boolean, nullable=False, default=False)
    default_ticket_order = Column(String, nullable=False, default=REVERSE_TICKET_ORDER)
    created_date = Column(DateTime, nullable=False, default=datetime.datetime.now())
    expired_date = Column(DateTime, nullable=True)

    books = relationship("Book", back_populates="game")
    game_number = Column(Integer, nullable=False, unique=True)

    def __repr__(self):
        """
        Returns a string representation of the game object.
        """
        return f"<Game(id={self.id}, name='{self.name}', price={self.price}, total_tickets={self.total_tickets}, game_number={self.game_number}, default_ticket_order='{self.default_ticket_order}', is_expired={self.is_expired})>"

class Book(Base):
    """
    Represents an instance of a book, often a specific print run or batch.

    Attributes:
        id (int): The primary key for the book.
        ticket_order (str): The order of tickets (e.g., "reverse", "forward").
                            Defaults to "reverse".
        is_active (bool): Whether this book is currently active for sales.
                          Defaults to True.
        activate_date (DateTime): The date when this book became active.
        finish_date (DateTime, optional): The date when this book was finished or deactivated.
        game_id (int): Foreign key referencing the `Game` this Book belongs to.
        game (relationship): The `Game` object this Book is associated with.
        sales_entries (relationship): A list of sales entries associated with this book.
        instance_number (int, optional): An optional instance number for this book.
    """
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticket_order = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    activate_date = Column(DateTime, nullable=False, default=datetime.datetime.now())
    finish_date = Column(DateTime, nullable=True)
    current_ticket_number = Column(Integer, nullable=False)

    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    game = relationship("Game", back_populates="books")

    sales_entries = relationship("SalesEntry", back_populates="book")
    book_number = Column(Integer, nullable=False)

    def __init__(self, **kwargs):
        """
        Initializes a new Book instance.
        """
        super().__init__(**kwargs)
        # Set the default ticket order based on the associated game
        if self.game and self.ticket_order is None:
            self.ticket_order = self.game.default_ticket_order

        if self.ticket_order == REVERSE_TICKET_ORDER:
            self.current_ticket_number = self.game.total_tickets
        else:
            self.current_ticket_number = 0


    def __repr__(self):
        """
        Returns a string representation of the BookInstance object.
        """
        return f"<Book(id={self.id}, game_id={self.game_id}, ticket_order='{self.ticket_order}', is_active={self.is_active}, activate_date={self.activate_date}, finish_date={self.finish_date})>"

class SalesEntry(Base):
    """
    Represents a sales entry for a book instance.

    Attributes:
        id (int): The primary key for the sales entry.
        start_number (int): The starting ticket number for this sale.
        end_number (int): The ending ticket number for this sale.
        date (DateTime): The date of the sale.
        count (int): The number of tickets sold in this entry.
                     Calculated based on start_number, end_number, and ticket_order.
        price (int): The total price for this sales entry.
                     Calculated based on count and book price.
        book_id (int): Foreign key referencing the `Book` of this sale.
        book (relationship): The `Book` object associated with this sale.
        user_id (int): Foreign key referencing the `User` who made this sale.
        user (relationship): The `User` object associated with this sale.
    """
    __tablename__ = "sales_entries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    start_number = Column(Integer, nullable=False)
    end_number = Column(Integer, nullable=False)
    date = Column(DateTime, nullable=False, default=datetime.datetime.now())
    count = Column(Integer, nullable=False) # This will be calculated
    price = Column(Integer, nullable=False) # This will be calculated

    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    book = relationship("Book", back_populates="sales_entries")

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User")

    def calculate_count_and_price(self):
        """
        Calculates and sets the 'count' and 'price' for this sales entry.

        The calculation depends on the 'ticket_order' of the associated
        book instance and the price per ticket of the associated book.
        This method should be called before saving the sales entry if
        'count' and 'price' are not manually set.
        """
        if self.book and self.book.game:
            if self.book.ticket_order == REVERSE_TICKET_ORDER:
                self.count = self.start_number - self.end_number
            else: # Assuming "forward" or any other order implies end_number > start_number
                self.count = self.end_number - self.start_number
            self.price = self.count * self.book.game.price
        else:
            self.count = 0
            self.price = 0

    def __repr__(self):
        """
        Returns a string representation of the SalesEntry object.
        """
        return f"<SalesEntry(id={self.id}, book_id={self.book_id}, user_id={self.user_id}, start_number={self.start_number}, end_number={self.end_number}, date={self.date}, count={self.count}, price={self.price})>"

class License(Base):
    __tablename__ = "license"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    is_active = Column(Boolean, nullable=False, default=False)

    def set_status(self, status: bool):
        self.is_active = status

    def __repr__(self):
        return f"<License(id={self.id}, is_active={self.is_active})>"
