import datetime
from typing import List, Dict, Tuple, Optional, Any

from sqlalchemy.orm import Session, joinedload

from app.constants import REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER, GAME_LENGTH, BOOK_LENGTH
from app.core.exceptions import ValidationError, DatabaseError, GameNotFoundError
from app.core.models import Book, SalesEntry
from app.data import crud_books, crud_games, crud_sales_entries


class SalesEntryService:
    def get_active_books_for_sales_display(self, db: Session) -> List[Book]:
        return db.query(Book).options(
            joinedload(Book.game)
        ).filter(
            Book.is_active == True,
            ).order_by(Book.game_id, Book.book_number).all()

    def get_or_create_book_for_sale(self, db: Session, game_number_str: str, book_number_str: str) -> Book:
        if not (game_number_str.isdigit() and len(game_number_str) == GAME_LENGTH):
            raise ValidationError(f"Game Number for scan must be {GAME_LENGTH} digits.")
        if not (book_number_str.isdigit() and len(book_number_str) == BOOK_LENGTH):
            raise ValidationError(f"Book Number for scan must be {BOOK_LENGTH} digits.")

        game_num_int = int(game_number_str)
        game = crud_games.get_game_by_game_number(db, game_num_int)

        if not game:
            raise GameNotFoundError(f"Game number '{game_number_str}' not found.")
        if game.is_expired:
            raise ValidationError(f"Game '{game.name}' (No: {game_number_str}) is expired. Cannot process sales.")

        book = db.query(Book).options(joinedload(Book.game)).filter(Book.game_id == game.id, Book.book_number == book_number_str).first()

        if not book:
            try:
                new_book = crud_books.create_book(db, game, book_number_str) # This now sets correct initial ticket numbers
                new_book.is_active = True
                new_book.activate_date = datetime.datetime.now()
                db.flush()
                db.refresh(new_book, attribute_names=['game'])
                print(f"SalesEntryService: Created/activated new book: ID {new_book.id}, Num {new_book.book_number}, Initial Ticket: {new_book.current_ticket_number}")
                return new_book
            except (DatabaseError, ValidationError) as e:
                raise DatabaseError(f"Could not create book {game_number_str}-{book_number_str}: {e.message if hasattr(e, 'message') else e}")
        else:
            if not book.game: db.refresh(book, attribute_names=['game'])
            if not book.is_active:
                book.is_active = True
                book.activate_date = datetime.datetime.now()
                book.finish_date = None
                print(f"SalesEntryService: Activated existing book: {book.book_number}, Initial Ticket: {book.current_ticket_number}")
            return book

    def process_and_save_sales_batch(
            self, db: Session, user_id: int, sales_item_details: List[Dict[str, Any]]
    ) -> Tuple[int, int, List[str]]:
        successful_sales_count = 0
        updated_books_count = 0
        error_messages: List[str] = []

        for detail_idx, detail in enumerate(sales_item_details):
            book_id = detail.get("book_db_id")
            # This is the book's current_ticket_number *before* this specific UI interaction session
            book_state_at_ui_load = detail.get("db_current_ticket_no")
            ui_target_state_str = detail.get("ui_new_ticket_no_str")
            all_sold_confirmed_by_ui = detail.get("all_tickets_sold_confirmed", False)

            book: Optional[Book] = db.query(Book).options(joinedload(Book.game)).filter(Book.id == book_id).first()

            if not book or not book.game:
                error_messages.append(f"Item {detail_idx+1}: Book ID {book_id} or its game data not found.")
                continue

            # Determine the final state for Book.current_ticket_number
            final_book_ticket_number_to_set: int
            is_valid_target_state = False

            if all_sold_confirmed_by_ui:
                if book.ticket_order == REVERSE_TICKET_ORDER:
                    final_book_ticket_number_to_set = -1 # State after selling ticket 0
                else: # FORWARD_TICKET_ORDER
                    final_book_ticket_number_to_set = book.game.total_tickets # State after selling ticket N-1
                is_valid_target_state = True
            elif ui_target_state_str is not None and ui_target_state_str.isdigit():
                parsed_num = int(ui_target_state_str)
                if -1 <= parsed_num <= book.game.total_tickets:
                    final_book_ticket_number_to_set = parsed_num
                    is_valid_target_state = True
                else:
                    error_messages.append(f"Item {detail_idx+1}: Invalid target ticket number '{ui_target_state_str}' for Book {book.book_number}.")
            else: # Empty or non-numeric ui_target_state_str and not all_sold_confirmed
                error_messages.append(f"Item {detail_idx+1}: No valid ticket entry for Book {book.book_number} and not confirmed 'all sold'. Skipped.")


            if not is_valid_target_state:
                continue # Skip this item

            # Use book_state_at_ui_load as the start_number for the SalesEntry
            sales_entry_start_number = book_state_at_ui_load
            sales_entry_end_number = final_book_ticket_number_to_set

            # Calculate actual tickets sold for this entry
            # This calculation should align with SalesEntry.calculate_count_and_price
            calculated_tickets_for_entry = 0
            if book.ticket_order == REVERSE_TICKET_ORDER:
                if sales_entry_start_number >= sales_entry_end_number : # e.g. start 99, end 0 -> 99 sold
                    calculated_tickets_for_entry = sales_entry_start_number - sales_entry_end_number
            else: # FORWARD_TICKET_ORDER
                if sales_entry_end_number >= sales_entry_start_number: # e.g. start 0, end 100 -> 100 sold
                    calculated_tickets_for_entry = sales_entry_end_number - sales_entry_start_number

            if calculated_tickets_for_entry < 0: # Should not happen if logic above is fine
                error_messages.append(f"Item {detail_idx+1}: Negative sales count for Book {book.book_number}. Start: {sales_entry_start_number}, End: {sales_entry_end_number}. Skipped.")
                continue

            if calculated_tickets_for_entry > 0 or all_sold_confirmed_by_ui: # Create entry if sales or explicit close
                try:
                    new_sales_entry = SalesEntry(
                        book_id=book.id, user_id=user_id,
                        start_number=sales_entry_start_number, # Book state *before* this transaction
                        end_number=sales_entry_end_number,     # Book state *after* this transaction
                        date=datetime.datetime.now(), book=book
                    )
                    new_sales_entry.calculate_count_and_price() # Uses its own start/end

                    # Ensure the count from SalesEntry matches our expectation for this specific transaction
                    if new_sales_entry.count != calculated_tickets_for_entry:
                        print(f"Warning: Discrepancy in calculated tickets for Book {book.book_number}. Service calc: {calculated_tickets_for_entry}, SalesEntry model calc: {new_sales_entry.count}. Using SalesEntry model count.")
                        # This might happen if SalesEntry's calculation is slightly different, e.g. handling of inclusive/exclusive
                        # For safety, rely on the SalesEntry model's calculation if different.

                    if new_sales_entry.count >= -1:
                        crud_sales_entries.create_sales_entry(db, new_sales_entry)
                        successful_sales_count += 1
                except Exception as e_sales:
                    error_messages.append(f"Item {detail_idx+1}: Error creating sales entry for Book {book.book_number}: {e_sales}")
                    continue

            # Update Book state
            try:
                book.current_ticket_number = final_book_ticket_number_to_set

                is_book_finished_now = False
                if book.ticket_order == REVERSE_TICKET_ORDER and final_book_ticket_number_to_set == -1:
                    is_book_finished_now = True
                elif book.ticket_order == FORWARD_TICKET_ORDER and final_book_ticket_number_to_set == book.game.total_tickets:
                    is_book_finished_now = True

                if all_sold_confirmed_by_ui or is_book_finished_now:
                    if book.is_active:
                        book.is_active = False
                        book.finish_date = datetime.datetime.now()
                updated_books_count += 1
            except Exception as e_book:
                error_messages.append(f"Item {detail_idx+1}: Error updating Book {book.book_number}: {e_book}")

        return successful_sales_count, updated_books_count, error_messages