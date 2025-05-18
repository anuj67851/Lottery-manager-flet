import datetime

from sqlalchemy.orm import Session # Added Session import
from sqlalchemy.exc import IntegrityError
from app.core.models import Game
from app.core.exceptions import DatabaseError, ValidationError, GameNotFoundError # Import custom exceptions


def get_game_by_game_number(db: Session, game_number: int) -> Game | None: # Type hint for game_number
    return db.query(Game).filter(Game.game_number == game_number).first()


def create_game(db: Session, game_name: str, price: int, total_tickets: int, game_number: int, order: str) -> Game: # price is int (cents)
    if not game_name:
        raise ValidationError("Game Name is required for creating a Game.")
    if price is None or price < 0: # price can be 0 for free games, but not negative
        raise ValidationError("Price is required and cannot be negative for creating a Game.")
    if not total_tickets or total_tickets <= 0:
        raise ValidationError("Total Tickets must be a positive number for creating a Game.")
    if not game_number or game_number <=0:
        raise ValidationError("Game Number must be a positive number for creating a Game.")
    if not order:
        raise ValidationError("Order is required for creating a Game.")

    existing_game = get_game_by_game_number(db, game_number)
    if existing_game:
        raise DatabaseError(f"Game with game number '{game_number}' already exists.")

    try:
        game = Game(
            name=game_name,
            price=price, # Expecting price in cents
            total_tickets=total_tickets,
            default_ticket_order=order,
            game_number=game_number,
        )
        db.add(game)
        db.commit()
        db.refresh(game)
        return game
    except IntegrityError as e: # Should be caught by pre-check, but as a fallback
        db.rollback()
        raise DatabaseError(f"Database threw an IntegrityError when adding new Game: {e.orig}") # Access original error
    except Exception as e:
        db.rollback()
        # Log the original exception e for debugging
        raise DatabaseError(f"Could not create game '{game_name}': An unexpected error occurred: {e}")


def get_all_games_sort_by_expiration_prices(db: Session) -> list[Game]: # Added Session type hint
    # Default sort: Active games first, then by price (low to high), then by game_number (low to high)
    return db.query(Game).order_by(Game.is_expired, Game.price, Game.game_number).all()


def get_game_by_id(db: Session, game_id: int) -> Game | None: # Added Session type hint and return None
    return db.query(Game).filter(Game.id == game_id).first()

def expire_game_in_db(db: Session, game_id: int) -> Game | None:
    game = get_game_by_id(db, game_id)
    if not game:
        raise GameNotFoundError(f"Game with ID {game_id} not found.")
    if game.is_expired: # Already expired
        return game

    game.is_expired = True
    game.expired_date = datetime.datetime.now() # Corrected: Use datetime.datetime.now

    # Deactivate all associated books
    for book in game.books:
        if book.is_active:
            book.is_active = False
            # Optionally set book.finish_date = datetime.datetime.now() if that's desired
            book.finish_date = datetime.datetime.now()
    try:
        db.commit()
        db.refresh(game)
        return game
    except Exception as e:
        db.rollback()
        raise DatabaseError(f"Could not expire game {game_id}: {e}")


def reactivate_game_in_db(db: Session, game_id: int) -> Game | None:
    game = get_game_by_id(db, game_id)
    if not game:
        raise GameNotFoundError(f"Game with ID {game_id} not found.")
    if not game.is_expired: # Already active
        return game

    game.is_expired = False
    game.expired_date = None
    # Note: Reactivating a game does NOT automatically reactivate its books.
    # This should be a conscious decision by the user in the UI for specific books.
    try:
        db.commit()
        db.refresh(game)
        return game
    except Exception as e:
        db.rollback()
        raise DatabaseError(f"Could not reactivate game {game_id}: {e}")
