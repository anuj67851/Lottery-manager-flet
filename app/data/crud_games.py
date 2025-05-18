import datetime

from sqlalchemy.orm import Session # Added Session import
from sqlalchemy.exc import IntegrityError
from app.core.models import Game, SalesEntry, Book
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

def has_game_ever_had_sales(db: Session, game_id: int) -> bool:
    """
    Checks if any book associated with the game has ever had a sales entry.
    This implies the book (and thus the game's structure at that time) was actively used.
    """
    return db.query(SalesEntry.id) \
        .join(Book) \
        .filter(Book.game_id == game_id) \
        .first() is not None

def update_game_details(db: Session, game: Game, updates: dict) -> Game:
    """
    Updates a game record with the provided dictionary of changes.
    Handles potential IntegrityError for game_number uniqueness.
    """
    original_game_number = game.game_number
    game_number_changed = False

    for key, value in updates.items():
        if hasattr(game, key):
            if key == "game_number" and value != original_game_number:
                game_number_changed = True
            setattr(game, key, value)
        else:
            # This should ideally not happen if 'updates' keys are validated beforehand
            print(f"Warning: Attribute {key} not found on Game model during update.")

    if game_number_changed:
        # Explicitly check if the new game_number is already taken by another game
        existing_game_with_new_number = db.query(Game).filter(
            Game.game_number == game.game_number,
            Game.id != game.id
        ).first()
        if existing_game_with_new_number:
            # To prevent commit from failing due to unique constraint,
            # revert game_number or raise specific error here.
            # For now, let's raise a DatabaseError that the service layer can catch.
            # Or, you could revert: game.game_number = original_game_number
            raise DatabaseError(f"Game number '{game.game_number}' is already in use by another game.")
    try:
        db.commit()
        db.refresh(game)
        return game
    except IntegrityError as e:
        db.rollback()
        # This might occur if the game_number check above had a race condition
        # or if other unique constraints are violated.
        if "game_number" in str(e.orig).lower(): # Check if it's about game_number
            raise DatabaseError(f"Game number '{updates.get('game_number', game.game_number)}' is already in use (IntegrityError).")
        raise DatabaseError(f"Database error updating game: {e.orig}")
    except Exception as e:
        db.rollback()
        raise DatabaseError(f"Could not update game details: {e}")
