from sqlalchemy.orm import Session

from app.core.models import Game
from app.core.exceptions import ValidationError
from app.constants import REVERSE_TICKET_ORDER
from app.data import crud_games


class GameService:

    def create_game(self, db: Session, game_name: str, price: float, total_tickets: int, game_number: int, order: str = REVERSE_TICKET_ORDER) -> Game:
        if not game_name or not price or not total_tickets or not game_number or not order:
            raise ValidationError("Game Name, Price, Total Tickets, Game Number and Order are required to create a Game.")
        return crud_games.create_game(db, game_name, price, total_tickets, game_number, order)
