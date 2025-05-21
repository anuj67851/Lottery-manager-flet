from typing import Optional, Union

from sqlalchemy.orm import Session
import re # For potential regex validation

from app.core.models import Game
from app.core.exceptions import ValidationError, GameNotFoundError, DatabaseError # Added DatabaseError
from app.constants import REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER
from app.data import crud_games

# Game validation constants
MIN_GAME_NAME_LENGTH = 3
MAX_GAME_NAME_LENGTH = 100
# Example: Regex for game name (allows letters, numbers, spaces, common punctuation like ' & -)
# Adjust as needed for business requirements.
GAME_NAME_REGEX = re.compile(r"^[a-zA-Z0-9\s'&.-]+$")

MIN_PRICE_DOLLARS = 0.00 # Price can be zero for free/promotional games
MAX_PRICE_DOLLARS = 1000.00 # Arbitrary reasonable upper limit

MIN_TOTAL_TICKETS = 1
MAX_TOTAL_TICKETS = 999 # Based on 3-digit ticket numbers (000-998 or 001-999) -> current_ticket_number related

MIN_GAME_NUMBER = 1
MAX_GAME_NUMBER = 999 # Game number is int, but often represented as 3 digits in QR


class GameService:

    def _validate_game_name(self, game_name: str):
        if not game_name:
            raise ValidationError("Game Name is required.")
        if not (MIN_GAME_NAME_LENGTH <= len(game_name) <= MAX_GAME_NAME_LENGTH):
            raise ValidationError(f"Game Name must be between {MIN_GAME_NAME_LENGTH} and {MAX_GAME_NAME_LENGTH} characters.")
        # if not GAME_NAME_REGEX.match(game_name): # Optional: if strict character control is needed
        #     raise ValidationError("Game Name contains invalid characters.")

    def _validate_price_dollars(self, price_dollars: Union[int, float]):
        if price_dollars is None:
            raise ValidationError("Price (dollars) is required.")
        try:
            price_val = float(price_dollars)
        except ValueError:
            raise ValidationError("Price must be a valid number.")
        if not (MIN_PRICE_DOLLARS <= price_val <= MAX_PRICE_DOLLARS):
            raise ValidationError(f"Price must be between ${MIN_PRICE_DOLLARS:.2f} and ${MAX_PRICE_DOLLARS:.2f}.")

    def _validate_total_tickets(self, total_tickets: int):
        if total_tickets is None: # Should be caught by int conversion if str
            raise ValidationError("Total Tickets is required.")
        if not isinstance(total_tickets, int): # Should be int by this point
            raise ValidationError("Total Tickets must be a whole number.")
        if not (MIN_TOTAL_TICKETS <= total_tickets <= MAX_TOTAL_TICKETS):
            raise ValidationError(f"Total Tickets must be between {MIN_TOTAL_TICKETS} and {MAX_TOTAL_TICKETS}.")

    def _validate_game_number(self, game_number: int):
        if game_number is None:
            raise ValidationError("Game Number is required.")
        if not isinstance(game_number, int):
            raise ValidationError("Game Number must be a whole number.")
        if not (MIN_GAME_NUMBER <= game_number <= MAX_GAME_NUMBER): # Example range
            raise ValidationError(f"Game Number must be between {MIN_GAME_NUMBER} and {MAX_GAME_NUMBER}.")

    def _validate_ticket_order(self, order: str):
        if not order:
            raise ValidationError("Ticket Order is required.")
        if order not in [REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER]:
            raise ValidationError(f"Invalid ticket order: '{order}'. Must be '{REVERSE_TICKET_ORDER}' or '{FORWARD_TICKET_ORDER}'.")


    def create_game(self, db: Session, game_name: str, price_dollars: Union[int, float], total_tickets: int, game_number: int, order: str = REVERSE_TICKET_ORDER) -> Game:
        game_name = game_name.strip()
        self._validate_game_name(game_name)
        self._validate_price_dollars(price_dollars)
        self._validate_total_tickets(total_tickets)
        self._validate_game_number(game_number)
        self._validate_ticket_order(order)

        try:
            price_in_cents = int(round(float(price_dollars) * 100))
            if price_in_cents < 0 : # Should be caught by _validate_price_dollars, but double check
                raise ValidationError("Price resulted in negative cents value after conversion.")
        except (TypeError, ValueError) as e:
            # This should ideally be caught by _validate_price_dollars if input was not numeric
            raise ValidationError(f"Invalid price format for conversion: {e}")

        # crud_games.create_game handles DatabaseError if game_number exists
        try:
            return crud_games.create_game(db, game_name, price_in_cents, total_tickets, game_number, order)
        except DatabaseError as e:
            raise e # Re-raise specific known errors
        except Exception as e_unhandled:
            raise DatabaseError(f"An unexpected error occurred in the database while creating game: {e_unhandled}")


    def get_all_games(self, db: Session) -> list[Game]:
        return crud_games.get_all_games_sort_by_expiration_prices(db)

    def get_game_by_id(self, db: Session, game_id: int) -> Game:
        game = crud_games.get_game_by_id(db, game_id)
        if not game:
            raise GameNotFoundError(f"Game with ID {game_id} not found.")
        return game

    def expire_game(self, db: Session, game_id: int) -> Game:
        # get_game_by_id will raise GameNotFoundError if not found
        game_to_expire = self.get_game_by_id(db, game_id)
        if game_to_expire.is_expired:
            return game_to_expire # Already expired
        try:
            return crud_games.expire_game_in_db(db, game_id)
        except DatabaseError as e:
            raise e
        except Exception as e_unhandled:
            raise DatabaseError(f"An unexpected error occurred in the database while expiring game: {e_unhandled}")


    def reactivate_game(self, db: Session, game_id: int) -> Game:
        game_to_reactivate = self.get_game_by_id(db, game_id)
        if not game_to_reactivate.is_expired:
            return game_to_reactivate # Already active
        try:
            return crud_games.reactivate_game_in_db(db, game_id)
        except DatabaseError as e:
            raise e
        except Exception as e_unhandled:
            raise DatabaseError(f"An unexpected error occurred in the database while reactivating game: {e_unhandled}")


    def check_game_had_sales(self, db: Session, game_id: int) -> bool:
        # No specific validation needed for this read operation parameter (id)
        return crud_games.has_game_ever_had_sales(db, game_id)

    def update_game(
            self,
            db: Session,
            game_id: int,
            name: Optional[str] = None,
            game_number: Optional[int] = None,
            price_dollars: Optional[Union[int, float]] = None,
            total_tickets: Optional[int] = None,
            default_ticket_order: Optional[str] = None
    ) -> Game:
        game_to_update = self.get_game_by_id(db, game_id) # Raises GameNotFoundError if not found

        updates: dict = {}
        restricted_fields_changed = False

        if name is not None:
            name = name.strip()
            self._validate_game_name(name)
            if name != game_to_update.name:
                updates["name"] = name

        if game_number is not None:
            self._validate_game_number(game_number)
            if game_number != game_to_update.game_number:
                updates["game_number"] = game_number

        can_change_restricted = not crud_games.has_game_ever_had_sales(db, game_id)

        if price_dollars is not None:
            self._validate_price_dollars(price_dollars)
            try:
                price_in_cents = int(round(float(price_dollars) * 100))
                if price_in_cents < 0: # Should be caught by _validate_price_dollars
                    raise ValidationError("Price resulted in negative cents value.")
            except (TypeError, ValueError) as e:
                raise ValidationError(f"Invalid price format for conversion: {e}")

            if price_in_cents != game_to_update.price:
                if can_change_restricted:
                    updates["price"] = price_in_cents
                    restricted_fields_changed = True
                else:
                    raise ValidationError("Price cannot be changed for games with sales history.")

        if total_tickets is not None:
            self._validate_total_tickets(total_tickets)
            if total_tickets != game_to_update.total_tickets:
                if can_change_restricted:
                    updates["total_tickets"] = total_tickets
                    restricted_fields_changed = True
                else:
                    raise ValidationError("Total tickets cannot be changed for games with sales history.")

        if default_ticket_order is not None:
            self._validate_ticket_order(default_ticket_order)
            if default_ticket_order != game_to_update.default_ticket_order:
                if can_change_restricted:
                    updates["default_ticket_order"] = default_ticket_order
                    restricted_fields_changed = True
                else:
                    raise ValidationError("Default ticket order cannot be changed for games with sales history.")

        if not updates:
            return game_to_update # No changes

        try:
            updated_game = crud_games.update_game_details(db, game_to_update, updates)
        except DatabaseError as e:
            raise e # Re-raise specific DB errors like unique constraint violation for game_number
        except Exception as e_unhandled:
            raise DatabaseError(f"An unexpected error occurred in the database while updating game: {e_unhandled}")


        if restricted_fields_changed and can_change_restricted:
            new_game_order = updated_game.default_ticket_order
            new_total_tickets = updated_game.total_tickets
            db.refresh(updated_game, attribute_names=['books']) # Ensure books are loaded
            for book in updated_game.books:
                # If associated books exist (which shouldn't have sales if can_change_restricted is true),
                # their properties dependent on game order or total tickets should be reset.
                book.ticket_order = new_game_order
                # Call model's internal logic to re-initialize current_ticket_number
                # based on the potentially new total_tickets and new_game_order.
                # This assumes Game object on Book is updated before _initialize_current_ticket_number is called.
                # Since `game_to_update` is the same object as `book.game`, its attributes are already updated.
                book._initialize_current_ticket_number() # This method uses self.game properties
        return updated_game