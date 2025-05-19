import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func

from app.core.models import SalesEntry, User, Book, Game

def get_sales_entries_for_report(
        db: Session,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        user_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Fetches sales entries for reporting, including related user, book, and game info.
    """
    stmt = (
        select(
            SalesEntry.date,
            User.username,
            Game.name.label("game_name"),
            Game.price.label("game_price"), # Price per ticket from Game model
            Book.book_number,
            Book.ticket_order,
            SalesEntry.start_number,
            SalesEntry.end_number,
            SalesEntry.count, # Tickets sold in this entry
            SalesEntry.price, # Total price for this sales entry (count * game_price)
        )
        .join(Book, SalesEntry.book_id == Book.id)
        .join(Game, Book.game_id == Game.id)
        .join(User, SalesEntry.user_id == User.id)
        .filter(SalesEntry.date >= start_date)
        .filter(SalesEntry.date <= end_date)
    )

    if user_id:
        stmt = stmt.filter(SalesEntry.user_id == user_id)

    stmt = stmt.order_by(SalesEntry.date.asc(), User.username.asc(), Game.name.asc(), Book.book_number.asc())

    results = db.execute(stmt).mappings().all()
    # Mappings() returns a list of RowMapping objects (dict-like)
    return [dict(row) for row in results]