from sqlalchemy.exc import IntegrityError
from app.core.models import Game
from app.core.exceptions import DatabaseError, ValidationError # Import custom exceptions


def get_game_by_game_number(db, game_number) -> Game:
    return db.query(Game).filter(Game.game_number == game_number).first()


def create_game(db, game_name, price, total_tickets, game_number, order) -> Game:
    if not game_name:
        raise ValidationError("Game Name is required for creating a Game.")
    if not price:
        raise ValidationError("Password is required for creating a Game.")
    if not total_tickets:
        raise ValidationError("Total Tickets is required for creating a Game.")
    if not game_number:
        raise ValidationError("Game Number is required for creating a Game.")
    if not order:
        raise ValidationError("Order is required for creating a Game.")

    existing_game = get_game_by_game_number(db, game_number)
    if existing_game:
        raise DatabaseError(f"Game with game number '{game_number}' already exists.")

    try:
        game = Game(
            name=game_name,
            price=price,
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
        raise DatabaseError(f"Database threw an IntegrityError when adding new Game: {e}")
    except Exception as e:
        db.rollback()
        # Log the original exception e for debugging
        raise DatabaseError(f"Could not create game '{game_name}': An unexpected error occurred: {e}")


def get_all_games_sort_by_expiration_prices(db) -> list[Game]:
    return db.query(Game).order_by(Game.is_expired).order_by(Game.price).all()


def get_game_by_id(db, game_id):
    return db.query(Game).filter(Game.id == game_id).first()