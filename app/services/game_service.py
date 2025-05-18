import datetime

from sqlalchemy.orm import Session

from app.core.models import Game
from app.core.exceptions import ValidationError, GameNotFoundError, DatabaseError
from app.constants import REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER # Added FORWARD_TICKET_ORDER
from app.data import crud_games


class GameService:

    def create_game(self, db: Session, game_name: str, price_cents: int, total_tickets: int, game_number: int, order: str = REVERSE_TICKET_ORDER) -> Game:
        if not game_name: # Basic validation, more complex rules could be here
            raise ValidationError("Game Name is required.")
        if price_cents is None or price_cents < 0:
            raise ValidationError("Price must be a non-negative value.")
        if not total_tickets or total_tickets <= 0:
            raise ValidationError("Total Tickets must be a positive number.")
        if not game_number or game_number <=0:
            raise ValidationError("Game Number must be a positive number.")
        if order not in [REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER]:
            raise ValidationError(f"Invalid ticket order specified: {order}.")

        # crud_games.create_game handles DatabaseError if game_number exists
        return crud_games.create_game(db, game_name, price_cents, total_tickets, game_number, order)

    def get_all_games(self, db: Session) -> list[Game]: # Added Session type hint
        return crud_games.get_all_games_sort_by_expiration_prices(db)

    def get_game_by_id(self, db: Session, game_id: int) -> Game | None: # Added Session type hint
        game = crud_games.get_game_by_id(db, game_id)
        if not game:
            raise GameNotFoundError(f"Game with ID {game_id} not found.")
        return game

    def expire_game(self, db: Session, game_id: int) -> Game:
        game = crud_games.get_game_by_id(db, game_id) # Fetch game first
        if not game:
            raise GameNotFoundError(f"Game with ID {game_id} not found to expire.")
        if game.is_expired:
            # Optionally raise an error or just return the game if already expired
            # print(f"Game {game_id} is already expired.")
            return game

        updated_game = crud_games.expire_game_in_db(db, game_id)
        if not updated_game: # Should not happen if game was found initially
            raise DatabaseError(f"Failed to expire game {game_id} after finding it.")
        return updated_game


    def reactivate_game(self, db: Session, game_id: int) -> Game:
        game = crud_games.get_game_by_id(db, game_id) # Fetch game first
        if not game:
            raise GameNotFoundError(f"Game with ID {game_id} not found to reactivate.")
        if not game.is_expired:
            # Optionally raise an error or just return the game if already active
            # print(f"Game {game_id} is already active.")
            return game

        updated_game = crud_games.reactivate_game_in_db(db, game_id)
        if not updated_game:  # Should not happen
            raise DatabaseError(f"Failed to reactivate game {game_id} after finding it.")
        return updated_game