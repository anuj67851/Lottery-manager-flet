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


def get_open_books_report_data(db: Session, game_id_filter: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Fetches data for currently active (open) books.
    Includes Game Name, Game No, Book No, Activation Date, Current Ticket, Order,
    Remaining Tickets, and Remaining Value.
    """
    query = (
        db.query(
            Game.name.label("game_name"),
            Game.game_number,
            Game.price.label("game_price_per_ticket"),
            Game.total_tickets.label("game_total_tickets"),
            Book.book_number,
            Book.activate_date,
            Book.current_ticket_number,
            Book.ticket_order,
            Book.is_active # For sanity check, should always be true
        )
        .join(Game, Book.game_id == Game.id)
        .filter(Book.is_active == True, Game.is_expired == False) # Only active books of active games
    )

    if game_id_filter:
        query = query.filter(Game.id == game_id_filter)

    query = query.order_by(Game.game_number, Book.book_number)

    results = []
    for row in query.all():
        # Re-fetch Book and Game instances to use properties/relationships if needed,
        # or construct remaining_tickets/value manually. For simplicity, fetch them.
        # This is slightly less efficient than doing it all in one SQL query if possible.
        book_instance = db.query(Book).options(joinedload(Book.game)).filter(
            Book.game_id == row.game_number, # Assuming game_number is unique and can be used to find game for book
            Book.book_number == row.book_number,
            Game.game_number == row.game_number # This part is tricky, need game_id from original query
            # Simpler: just query Book by ID if ID was selected
        ).first() # This query is problematic. Let's reconstruct with the original models.

        # Let's iterate through Book objects directly to use the new properties

    # Corrected approach for Open Books Report Data
    book_query = db.query(Book).options(joinedload(Book.game)).filter(
        Book.is_active == True,
        Game.is_expired == False # Accessing Game.is_expired requires a join
    ).join(Book.game) # Ensure the join is explicit for the filter

    if game_id_filter:
        book_query = book_query.filter(Game.id == game_id_filter)

    active_books = book_query.order_by(Game.game_number, Book.book_number).all()

    report_data = []
    for book in active_books:
        if book.game: # Ensure game relationship is loaded
            report_data.append({
                "game_name": book.game.name,
                "game_number": book.game.game_number,
                "book_number": book.book_number,
                "activate_date": book.activate_date,
                "current_ticket_number": book.current_ticket_number,
                "ticket_order": book.ticket_order,
                "remaining_tickets": book.remaining_tickets, # Using the new property
                "game_price_per_ticket": book.game.price,
                "remaining_value": book.remaining_value, # Using the new property
                "game_total_tickets": book.game.total_tickets,
            })
    return report_data


def get_game_expiry_report_data(
        db: Session,
        status_filter: Optional[str] = None, # "active", "expired"
        expired_start_date: Optional[datetime.datetime] = None,
        expired_end_date: Optional[datetime.datetime] = None
) -> List[Dict[str, Any]]:
    """
    Fetches game data based on expiry status and optional date range for expired games.
    """
    query = db.query(
        Game.name,
        Game.game_number,
        Game.price,
        Game.total_tickets,
        Game.is_expired,
        Game.created_date,
        Game.expired_date
    )

    if status_filter:
        if status_filter.lower() == "expired":
            query = query.filter(Game.is_expired == True)
            if expired_start_date and expired_end_date:
                # Ensure end_date includes the whole day
                end_datetime_inclusive = expired_end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                query = query.filter(Game.expired_date >= expired_start_date, Game.expired_date <= end_datetime_inclusive)
            elif expired_start_date:
                query = query.filter(Game.expired_date >= expired_start_date)
            elif expired_end_date:
                end_datetime_inclusive = expired_end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                query = query.filter(Game.expired_date <= end_datetime_inclusive)
        elif status_filter.lower() == "active":
            query = query.filter(Game.is_expired == False)
            # Date range filter is not applicable for active games based on 'expired_date'

    # Default sort: Expired games first, then by game number
    results = query.order_by(Game.is_expired.desc(), Game.game_number.asc()).all()
    return [dict(row._mapping) for row in results]


def get_stock_levels_report_data(db: Session, game_id_filter: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Aggregates book stock levels per game.
    """
    # Subquery to count total books per game
    total_books_sq = (
        select(Book.game_id, func.count(Book.id).label("total_book_count"))
        .group_by(Book.game_id)
        .subquery()
    )
    # Subquery to count active books per game
    active_books_sq = (
        select(Book.game_id, func.count(Book.id).label("active_book_count"))
        .filter(Book.is_active == True)
        .group_by(Book.game_id)
        .subquery()
    )
    # Subquery to count finished books per game
    finished_books_sq = (
        select(Book.game_id, func.count(Book.id).label("finished_book_count"))
        .filter(Book.finish_date != None) # SQLAlchemy: use != None for IS NOT NULL
        .group_by(Book.game_id)
        .subquery()
    )
    # Subquery to count pending books (inactive, not activated, not finished)
    pending_books_sq = (
        select(Book.game_id, func.count(Book.id).label("pending_book_count"))
        .filter(Book.is_active == False, Book.activate_date == None, Book.finish_date == None)
        .group_by(Book.game_id)
        .subquery()
    )

    # Main query joining Game with subqueries
    stmt = (
        select(
            Game.id.label("game_id"), # Added game_id for joining active stock value calculation
            Game.name.label("game_name"),
            Game.game_number,
            Game.price.label("game_price_per_ticket"),
            func.coalesce(total_books_sq.c.total_book_count, 0).label("total_books"),
            func.coalesce(active_books_sq.c.active_book_count, 0).label("active_books"),
            func.coalesce(finished_books_sq.c.finished_book_count, 0).label("finished_books"),
            func.coalesce(pending_books_sq.c.pending_book_count, 0).label("pending_books")
        )
        .outerjoin(total_books_sq, Game.id == total_books_sq.c.game_id)
        .outerjoin(active_books_sq, Game.id == active_books_sq.c.game_id)
        .outerjoin(finished_books_sq, Game.id == finished_books_sq.c.game_id)
        .outerjoin(pending_books_sq, Game.id == pending_books_sq.c.game_id)
        .filter(Game.is_expired == False) # Typically stock report is for active games
    )

    if game_id_filter:
        stmt = stmt.filter(Game.id == game_id_filter)

    stmt = stmt.order_by(Game.game_number)

    game_stock_summary = db.execute(stmt).mappings().all()

    report_data = []
    for summary_row_map in game_stock_summary:
        summary_row = dict(summary_row_map) # Convert RowMapping to dict
        # Calculate value of active stock for this game
        active_stock_value = 0
        game_id = summary_row['game_id'] # Use the fetched game_id

        active_books_for_this_game = db.query(Book).options(joinedload(Book.game)).filter(
            Book.game_id == game_id,
            Book.is_active == True
        ).all()

        for book in active_books_for_this_game:
            active_stock_value += book.remaining_value

        summary_row["active_stock_value"] = active_stock_value
        report_data.append(summary_row)

    return report_data