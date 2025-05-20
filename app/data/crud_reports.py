import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func as sql_func # aliased func to sql_func

from app.core.models import SalesEntry, User, Book, Game, ShiftSubmission

def get_sales_entries_for_report(
        db: Session,
        start_submission_date: datetime.datetime,
        end_submission_date: datetime.datetime,
        user_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    stmt = (
        select(
            SalesEntry.date.label("sales_entry_creation_date"),
            ShiftSubmission.submission_datetime.label("shift_submission_datetime"),
            User.username,
            Game.name.label("game_name"),
            Game.game_number.label("game_number_actual"),
            Game.price.label("ticket_price_actual"),
            Book.book_number.label("book_number_actual"),
            Book.ticket_order,
            SalesEntry.start_number,
            SalesEntry.end_number,
            SalesEntry.count,
            SalesEntry.price.label("sales_entry_total_value"),
            ShiftSubmission.id.label("shift_id")
        )
        .join(ShiftSubmission, SalesEntry.shift_id == ShiftSubmission.id)
        .join(User, ShiftSubmission.user_id == User.id)
        .join(Book, SalesEntry.book_id == Book.id)
        .join(Game, Book.game_id == Game.id)
        .filter(ShiftSubmission.submission_datetime >= start_submission_date)
        .filter(ShiftSubmission.submission_datetime <= end_submission_date)
    )
    if user_id:
        stmt = stmt.filter(ShiftSubmission.user_id == user_id)
    stmt = stmt.order_by(
        ShiftSubmission.submission_datetime.asc(), User.username.asc(),
        Game.name.asc(), Book.book_number.asc(), SalesEntry.date.asc()
    )
    results = db.execute(stmt).mappings().all()
    return [dict(row) for row in results]

# --- Other report CRUD methods (get_open_books_report_data, etc.) remain unchanged ---
def get_open_books_report_data(db: Session, game_id_filter: Optional[int] = None) -> List[Dict[str, Any]]:
    book_query = db.query(Book).options(joinedload(Book.game)).filter(
        Book.is_active == True, Game.is_expired == False
    ).join(Book.game)
    if game_id_filter: book_query = book_query.filter(Game.id == game_id_filter)
    active_books = book_query.order_by(Game.game_number, Book.book_number).all()
    report_data = []
    for book in active_books:
        if book.game:
            report_data.append({
                "game_name": book.game.name, "game_number": book.game.game_number,
                "book_number": book.book_number, "activate_date": book.activate_date,
                "current_ticket_number": book.current_ticket_number, "ticket_order": book.ticket_order,
                "remaining_tickets": book.remaining_tickets, "game_price_per_ticket": book.game.price,
                "remaining_value": book.remaining_value, "game_total_tickets": book.game.total_tickets,
            })
    return report_data

def get_game_expiry_report_data(
        db: Session, status_filter: Optional[str] = None,
        expired_start_date: Optional[datetime.datetime] = None,
        expired_end_date: Optional[datetime.datetime] = None
) -> List[Dict[str, Any]]:
    query = db.query( Game.name, Game.game_number, Game.price, Game.total_tickets,
                      Game.is_expired, Game.created_date, Game.expired_date )
    if status_filter:
        if status_filter.lower() == "expired":
            query = query.filter(Game.is_expired == True)
            if expired_start_date and expired_end_date:
                end_dt_inc = expired_end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                query = query.filter(Game.expired_date >= expired_start_date, Game.expired_date <= end_dt_inc)
            elif expired_start_date: query = query.filter(Game.expired_date >= expired_start_date)
            elif expired_end_date:
                end_dt_inc = expired_end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                query = query.filter(Game.expired_date <= end_dt_inc)
        elif status_filter.lower() == "active": query = query.filter(Game.is_expired == False)
    results = query.order_by(Game.is_expired.desc(), Game.game_number.asc()).all()
    return [dict(row._mapping) for row in results]

def get_stock_levels_report_data(db: Session, game_id_filter: Optional[int] = None) -> List[Dict[str, Any]]:
    total_books_sq = ( select(Book.game_id, sql_func.count(Book.id).label("total_book_count"))
                       .group_by(Book.game_id).subquery() )
    active_books_sq = ( select(Book.game_id, sql_func.count(Book.id).label("active_book_count"))
                        .filter(Book.is_active == True).group_by(Book.game_id).subquery() )
    finished_books_sq = ( select(Book.game_id, sql_func.count(Book.id).label("finished_book_count"))
                          .filter(Book.finish_date != None).group_by(Book.game_id).subquery() )
    pending_books_sq = ( select(Book.game_id, sql_func.count(Book.id).label("pending_book_count"))
                         .filter(Book.is_active == False, Book.activate_date == None, Book.finish_date == None)
                         .group_by(Book.game_id).subquery() )
    stmt = ( select( Game.id.label("game_id"), Game.name.label("game_name"), Game.game_number,
                     Game.price.label("game_price_per_ticket"),
                     sql_func.coalesce(total_books_sq.c.total_book_count, 0).label("total_books"),
                     sql_func.coalesce(active_books_sq.c.active_book_count, 0).label("active_books"),
                     sql_func.coalesce(finished_books_sq.c.finished_book_count, 0).label("finished_books"),
                     sql_func.coalesce(pending_books_sq.c.pending_book_count, 0).label("pending_books") )
             .outerjoin(total_books_sq, Game.id == total_books_sq.c.game_id)
             .outerjoin(active_books_sq, Game.id == active_books_sq.c.game_id)
             .outerjoin(finished_books_sq, Game.id == finished_books_sq.c.game_id)
             .outerjoin(pending_books_sq, Game.id == pending_books_sq.c.game_id)
             .filter(Game.is_expired == False) )
    if game_id_filter: stmt = stmt.filter(Game.id == game_id_filter)
    stmt = stmt.order_by(Game.game_number)
    game_stock_summary = db.execute(stmt).mappings().all()
    report_data = []
    for summary_row_map in game_stock_summary:
        summary_row = dict(summary_row_map)
        active_stock_value = 0; game_id = summary_row['game_id']
        active_books = db.query(Book).options(joinedload(Book.game)).filter(
            Book.game_id == game_id, Book.is_active == True ).all()
        for book in active_books: active_stock_value += book.remaining_value
        summary_row["active_stock_value"] = active_stock_value
        report_data.append(summary_row)
    return report_data