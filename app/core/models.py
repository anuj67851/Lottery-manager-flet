"""
Defines the SQLAlchemy models for the application.

This module contains the database schema definitions using SQLAlchemy's
declarative base. It includes the `User`, `Book`, `BookInstance`,
and `SalesEntry` models.
"""
import bcrypt
from sqlalchemy import String, Integer, Column, ForeignKey, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

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
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="employee")

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

class Book(Base):
    """
    Represents a book in the system.

    Attributes:
        id (int): The primary key for the book.
        name (str): The unique name of the book.
        price (int): The price of one ticket for the book.
        total_tickets (int): The total number of tickets available for this book type.
        book_instances (relationship): A list of book instances associated with this book.
        series_number (int, optional): An optional series number for the book.
    """
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    price = Column(Integer, nullable=False)
    total_tickets = Column(Integer, nullable=False)

    book_instances = relationship("BookInstance", back_populates="book")
    series_number = Column(Integer, nullable=True)
    
    def __repr__(self):
        """
        Returns a string representation of the Book object.
        """
        return f"<Book(id={self.id}, name='{self.name}', price={self.price}, total_tickets={self.total_tickets})>"

class BookInstance(Base):
    """
    Represents an instance of a book, often a specific print run or batch.

    Attributes:
        id (int): The primary key for the book instance.
        ticket_order (str): The order of tickets (e.g., "reverse", "forward").
                            Defaults to "reverse".
        is_active (bool): Whether this book instance is currently active for sales.
                          Defaults to True.
        activate_date (DateTime): The date when this book instance became active.
        finish_date (DateTime, optional): The date when this book instance was finished or deactivated.
        book_id (int): Foreign key referencing the `Book` this instance belongs to.
        book (relationship): The `Book` object this instance is associated with.
        sales_entries (relationship): A list of sales entries associated with this book instance.
        instance_number (int, optional): An optional instance number for this book instance.
    """
    __tablename__ = "book_instance"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticket_order = Column(String, nullable=False, default="reverse")
    is_active = Column(Boolean, nullable=False, default=True)
    activate_date = Column(DateTime, nullable=False)
    finish_date = Column(DateTime, nullable=True)
    
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    book = relationship("Book", back_populates="book_instances")

    sales_entries = relationship("SalesEntry", back_populates="book_instance")
    instance_number = Column(Integer, nullable=True)
    
    def __repr__(self):
        """
        Returns a string representation of the BookInstance object.
        """
        return f"<BookInstance(id={self.id}, book_id={self.book_id}, ticket_order='{self.ticket_order}', is_active={self.is_active}, activate_date={self.activate_date}, finish_date={self.finish_date})>"

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
        book_instance_id (int): Foreign key referencing the `BookInstance` of this sale.
        book_instance (relationship): The `BookInstance` object associated with this sale.
        user_id (int): Foreign key referencing the `User` who made this sale.
        user (relationship): The `User` object associated with this sale.
    """
    __tablename__ = "sales_entry"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    start_number = Column(Integer, nullable=False)
    end_number = Column(Integer, nullable=False)
    date = Column(DateTime, nullable=False)
    count = Column(Integer, nullable=False) # This will be calculated
    price = Column(Integer, nullable=False) # This will be calculated

    book_instance_id = Column(Integer, ForeignKey("book_instance.id"), nullable=False)
    book_instance = relationship("BookInstance", back_populates="sales_entries")
    
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
        if self.book_instance and self.book_instance.book:
            if self.book_instance.ticket_order == "reverse":
                self.count = self.start_number - self.end_number
            else: # Assuming "forward" or any other order implies end_number > start_number
                self.count = self.end_number - self.start_number
            self.price = self.count * self.book_instance.book.price
        else:
            # Handle cases where book_instance or book_instance.book might be None,
            # though SQLAlchemy relationships usually prevent this if accessed after commit.
            # You might want to raise an error or log a warning here.
            self.count = 0
            self.price = 0
    
    def __repr__(self):
        """
        Returns a string representation of the SalesEntry object.
        """
        return f"<SalesEntry(id={self.id}, book_instance_id={self.book_instance_id}, user_id={self.user_id}, start_number={self.start_number}, end_number={self.end_number}, date={self.date}, count={self.count}, price={self.price})>"