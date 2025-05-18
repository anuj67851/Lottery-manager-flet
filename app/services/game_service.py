import datetime

from sqlalchemy.orm import Session

from app.core.models import Game
from app.core.exceptions import ValidationError, GameNotFoundError
from app.constants import REVERSE_TICKET_ORDER
from app.data import crud_games


class GameService:

    def create_game(self, db: Session, game_name: str, price: float, total_tickets: int, game_number: int, order: str = REVERSE_TICKET_ORDER) -> Game:
        if not game_name or not price or not total_tickets or not game_number or not order:
            raise ValidationError("Game Name, Price, Total Tickets, Game Number and Order are required to create a Game.")
        return crud_games.create_game(db, game_name, price, total_tickets, game_number, order)

    def get_all_games(self, db):
        return crud_games.get_all_games_sort_by_expiration_prices(db)

    def get_game_by_id(self, db, game_id):
        return crud_games.get_game_by_id(db, game_id)
    def expire_game(self, db: Session, game_id: int):
        game = self.get_game_by_id(db, game_id)
        if not game:
            raise GameNotFoundError(f"Game with ID {game_id} not found.")

        game.is_expired = True
        game.expired_date = datetime.datetime.now()

        for book in game.books:
            book.is_active = False

        db.commit()

    def reactivate_game(self, db: Session, game_id: int):
        game = self.get_game_by_id(db, game_id)
        if not game:
            raise GameNotFoundError(f"Game with ID {game_id} not found.")
        game.is_expired = False
        game.expired_date = None
        db.commit()
