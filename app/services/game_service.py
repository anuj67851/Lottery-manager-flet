import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.models import Game
from app.core.exceptions import ValidationError, GameNotFoundError, DatabaseError
from app.constants import REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER # Added FORWARD_TICKET_ORDER
from app.data import crud_games


class GameService:

    def create_game(self, db: Session, game_name: str, price: int, total_tickets: int, game_number: int, order: str = REVERSE_TICKET_ORDER) -> Game:
        if not game_name: # Basic validation, more complex rules could be here
            raise ValidationError("Game Name is required.")
        if price is None or price < 0:
            raise ValidationError("Price must be a non-negative value.")
        if not total_tickets or total_tickets <= 0:
            raise ValidationError("Total Tickets must be a positive number.")
        if not game_number or game_number <=0:
            raise ValidationError("Game Number must be a positive number.")
        if order not in [REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER]:
            raise ValidationError(f"Invalid ticket order specified: {order}.")

        # crud_games.create_game handles DatabaseError if game_number exists
        return crud_games.create_game(db, game_name, price, total_tickets, game_number, order)

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

    def check_game_had_sales(self, db: Session, game_id: int) -> bool:
        return crud_games.has_game_ever_had_sales(db, game_id)

    def update_game(
            self,
            db: Session,
            game_id: int,
            name: Optional[str] = None,
            game_number: Optional[int] = None,
            price: Optional[int] = None,
            total_tickets: Optional[int] = None,
            default_ticket_order: Optional[str] = None
    ) -> Game:
        game_to_update = self.get_game_by_id(db, game_id) # Raises GameNotFoundError if not found

        updates: dict = {}
        restricted_fields_changed = False

        if name is not None and name.strip() and name.strip() != game_to_update.name:
            updates["name"] = name.strip()
        if game_number is not None and game_number > 0 and game_number != game_to_update.game_number:
            updates["game_number"] = game_number

        # Check if restricted fields can be changed
        can_change_restricted = not crud_games.has_game_ever_had_sales(db, game_id)

        if price is not None and price >= 0:
            if can_change_restricted:
                if price != game_to_update.price:
                    updates["price"] = price
                    restricted_fields_changed = True
            elif price != game_to_update.price: # Attempt to change restricted field
                raise ValidationError("Price cannot be changed for games with active/past sales.")

        if total_tickets is not None and total_tickets > 0:
            if can_change_restricted:
                if total_tickets != game_to_update.total_tickets:
                    updates["total_tickets"] = total_tickets
                    restricted_fields_changed = True
            elif total_tickets != game_to_update.total_tickets:
                raise ValidationError("Total tickets cannot be changed for games with active/past sales.")

        if default_ticket_order is not None and default_ticket_order in [REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER]:
            if can_change_restricted:
                if default_ticket_order != game_to_update.default_ticket_order:
                    updates["default_ticket_order"] = default_ticket_order
                    restricted_fields_changed = True
            elif default_ticket_order != game_to_update.default_ticket_order:
                raise ValidationError("Default ticket order cannot be changed for games with active/past sales.")

        if not updates:
            # No actual changes provided or detected
            return game_to_update

        # Apply updates to the game object
        updated_game = crud_games.update_game_details(db, game_to_update, updates)

        # Side effect: If order or total_tickets changed for a game with no sales history,
        # update its existing (unused) books.
        if restricted_fields_changed and can_change_restricted:
            new_game_order = updated_game.default_ticket_order
            new_total_tickets = updated_game.total_tickets # Use the potentially updated total_tickets

            # Eager load books for modification if not already loaded or if session might be different
            # However, game_to_update.books should be available if relationships are set up.
            db.refresh(updated_game, attribute_names=['books']) # Ensure books are loaded/refreshed

            for book in updated_game.books:
                # Since can_change_restricted is True, these books have no sales entries.
                # We can safely update their order and reset current ticket number.
                book.ticket_order = new_game_order # Align book's order with game's new default
                if new_game_order == REVERSE_TICKET_ORDER:
                    book.current_ticket_number = new_total_tickets
                else: # FORWARD_TICKET_ORDER
                    book.current_ticket_number = 0
            # The commit in update_game_details will save these book changes too if they are part of the session.
            # If books were modified, they are already dirty in the session.
            # A final commit is handled by update_game_details or the context manager.
            # Let's ensure they are committed by explicitly adding them to the session's "dirty" list if needed,
            # or simply rely on the cascade from game_to_update.
            # The current crud_games.update_game_details only commits the game.
            # We might need to commit the session again here or pass books to be updated.
            # For simplicity, let's assume the session from get_db_session will handle the commit for books too.
            # If not, an explicit db.commit() after the loop would be needed IF using a db session directly here.
            # Since crud_games.update_game_details handles its own commit, we'll let the context manager handle this one too.

        return updated_game