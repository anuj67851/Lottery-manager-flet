import datetime
from typing import List, Dict, Tuple, Optional, Any

from sqlalchemy.orm import Session, joinedload

from app.constants import REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER, GAME_LENGTH, BOOK_LENGTH
from app.core.exceptions import ValidationError, DatabaseError, GameNotFoundError
from app.core.models import Book, SalesEntry, Game as GameModel, ShiftSubmission # Added ShiftSubmission
from app.data import crud_books, crud_games, crud_sales_entries


class SalesEntryService:
    def get_active_books_for_sales_display(self, db: Session) -> List[Book]:
        return db.query(Book).options(
            joinedload(Book.game)
        ).filter(
            Book.is_active == True,
            GameModel.is_expired == False # Ensure game is also not expired
        ).join(Book.game).order_by(Book.game_id, Book.book_number).all()

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
                new_book = crud_books.create_book(db, game, book_number_str)
                new_book.is_active = True
                new_book.activate_date = datetime.datetime.now()
                # db.flush() # Let ShiftService manage flushes within its transaction
                # db.refresh(new_book, attribute_names=['game']) # Refresh if needed for immediate use
                print(f"SalesEntryService: Created/activated new book: ID {new_book.id}, Num {new_book.book_number}, Initial Ticket: {new_book.current_ticket_number}")
                return new_book
            except (DatabaseError, ValidationError) as e:
                raise DatabaseError(f"Could not create book {game_number_str}-{book_number_str} for sale: {e.message if hasattr(e, 'message') else e}")
        else:
            if not book.game: db.refresh(book, attribute_names=['game'])
            if not book.is_active:
                if book.ticket_order == REVERSE_TICKET_ORDER and book.current_ticket_number == -1:
                    raise ValidationError(f"Book '{book.book_number}' is already sold out (Reverse). Cannot use for sales.")
                if book.ticket_order == FORWARD_TICKET_ORDER and book.game and book.current_ticket_number == book.game.total_tickets:
                    raise ValidationError(f"Book '{book.book_number}' is already sold out (Forward). Cannot use for sales.")

                book.is_active = True
                book.activate_date = datetime.datetime.now()
                book.finish_date = None
                print(f"SalesEntryService: Activated existing book for sale: {book.book_number}, Current Ticket: {book.current_ticket_number}")
            return book

    def create_sales_entry_for_full_book(self, db: Session, book: Book, shift_id: int) -> SalesEntry: # Changed user_id to shift_id
        """
        Creates a SalesEntry record for a book that has been marked as fully sold.
        Links the SalesEntry to the provided shift_id.
        Assumes the book's current_ticket_number and status have already been updated.
        """
        if not book.game:
            raise DatabaseError(f"Book ID {book.id} is missing game data for full sale entry.")

        original_start_number = 0
        if book.ticket_order == REVERSE_TICKET_ORDER:
            original_start_number = book.game.total_tickets -1
        else: # FORWARD_TICKET_ORDER
            original_start_number = 0

        final_end_number = book.current_ticket_number

        sales_entry = SalesEntry(
            book_id=book.id,
            shift_id=shift_id, # Set shift_id
            start_number=original_start_number,
            end_number=final_end_number,
            date=datetime.datetime.now(),
            book=book
        )
        sales_entry.calculate_count_and_price()

        if sales_entry.count != book.game.total_tickets:
            print(f"Warning: Full book sale for Book ID {book.id} resulted in count {sales_entry.count}, expected {book.game.total_tickets}.")

        return crud_sales_entries.create_sales_entry(db, sales_entry)


    def process_and_save_sales_batch_for_shift( # Renamed and signature changed
            self, db: Session, shift_id: int, sales_item_details: List[Dict[str, Any]]
    ) -> Tuple[int, int, List[str]]:
        """
        Processes a batch of sales item details and creates SalesEntry records,
        linking them to the provided shift_id.
        It does NOT update shift aggregates; that's handled by ShiftService.
        """
        successful_sales_count = 0
        updated_books_count = 0 # Tracks books whose current_ticket_number or active status changed
        error_messages: List[str] = []

        for detail_idx, detail in enumerate(sales_item_details):
            book_id = detail.get("book_db_id")
            book_state_at_ui_load = detail.get("db_current_ticket_no")
            ui_target_state_str = detail.get("ui_new_ticket_no_str")
            all_sold_confirmed_by_ui = detail.get("all_tickets_sold_confirmed", False)

            book: Optional[Book] = db.query(Book).options(joinedload(Book.game)).filter(Book.id == book_id).first()

            if not book or not book.game:
                error_messages.append(f"Item {detail_idx+1}: Book ID {book_id} or its game data not found.")
                continue

            final_book_ticket_number_to_set: int
            is_valid_target_state = False

            if all_sold_confirmed_by_ui:
                if book.ticket_order == REVERSE_TICKET_ORDER:
                    final_book_ticket_number_to_set = -1
                else: # FORWARD_TICKET_ORDER
                    final_book_ticket_number_to_set = book.game.total_tickets
                is_valid_target_state = True
            elif ui_target_state_str is not None and (ui_target_state_str == "-1" or ui_target_state_str.isdigit()):
                try:
                    parsed_num = int(ui_target_state_str)
                    is_range_ok = False
                    if book.ticket_order == REVERSE_TICKET_ORDER:
                        is_range_ok = (-1 <= parsed_num <= book_state_at_ui_load)
                    else:
                        is_range_ok = (book_state_at_ui_load <= parsed_num <= book.game.total_tickets)

                    if is_range_ok:
                        final_book_ticket_number_to_set = parsed_num
                        is_valid_target_state = True
                    else:
                        range_hint = f"between -1 and {book_state_at_ui_load}" if book.ticket_order == REVERSE_TICKET_ORDER else f"between {book_state_at_ui_load} and {book.game.total_tickets}"
                        error_messages.append(f"Item {detail_idx+1}: Invalid target ticket '{ui_target_state_str}' for Book {book.book_number}. Expected {range_hint}.")
                except ValueError:
                    error_messages.append(f"Item {detail_idx+1}: Non-integer target ticket '{ui_target_state_str}' for Book {book.book_number}.")
            else:
                error_messages.append(f"Item {detail_idx+1}: No valid ticket entry for Book {book.book_number} and not 'all sold'. Skipped.")


            if not is_valid_target_state:
                continue

            sales_entry_start_number = book_state_at_ui_load
            sales_entry_end_number = final_book_ticket_number_to_set

            calculated_tickets_for_this_entry = 0
            if book.ticket_order == REVERSE_TICKET_ORDER:
                if sales_entry_start_number >= sales_entry_end_number:
                    calculated_tickets_for_this_entry = sales_entry_start_number - sales_entry_end_number
            else: # FORWARD_TICKET_ORDER
                if sales_entry_end_number >= sales_entry_start_number:
                    calculated_tickets_for_this_entry = sales_entry_end_number - sales_entry_start_number

            if calculated_tickets_for_this_entry < 0: # Should not happen if logic is correct
                error_messages.append(f"Item {detail_idx+1}: Negative sales calc for Book {book.book_number}. Start: {sales_entry_start_number}, End: {sales_entry_end_number}. Skipped.")
                continue

            if calculated_tickets_for_this_entry > 0 or (all_sold_confirmed_by_ui and calculated_tickets_for_this_entry >= 0):
                # Create SalesEntry only if there's a sale or explicit "all sold"
                try:
                    new_sales_entry = SalesEntry(
                        book_id=book.id,
                        shift_id=shift_id, # Link to the current shift
                        start_number=sales_entry_start_number,
                        end_number=sales_entry_end_number,
                        date=datetime.datetime.now(), # Date of this specific sales entry creation
                        book=book
                    )
                    new_sales_entry.calculate_count_and_price()

                    if new_sales_entry.count != calculated_tickets_for_this_entry:
                        print(f"Warning: Discrepancy in tickets for Book {book.book_number} (Shift {shift_id}). Service: {calculated_tickets_for_this_entry}, Model: {new_sales_entry.count}. Using Model.")

                    if new_sales_entry.count >= 0:
                        crud_sales_entries.create_sales_entry(db, new_sales_entry)
                        successful_sales_count += 1
                    elif new_sales_entry.count < 0:
                        error_messages.append(f"Item {detail_idx+1}: SalesEntry model calculated negative count for Book {book.book_number} (Shift {shift_id}). Skipped sales record.")
                        continue
                except Exception as e_sales:
                    error_messages.append(f"Item {detail_idx+1}: Error creating sales entry for Book {book.book_number} (Shift {shift_id}): {e_sales}")
                    continue

                    # Update Book state
            if book.current_ticket_number != final_book_ticket_number_to_set:
                book.current_ticket_number = final_book_ticket_number_to_set
                if not detail.get("_book_already_counted_as_updated"): # Avoid double counting if book appears multiple times in batch
                    updated_books_count += 1
                    detail["_book_already_counted_as_updated"] = True # Mark as updated for this batch

            is_book_finished_after_this_sale = False
            if book.ticket_order == REVERSE_TICKET_ORDER and final_book_ticket_number_to_set == -1:
                is_book_finished_after_this_sale = True
            elif book.ticket_order == FORWARD_TICKET_ORDER and final_book_ticket_number_to_set == book.game.total_tickets:
                is_book_finished_after_this_sale = True

            if all_sold_confirmed_by_ui or is_book_finished_after_this_sale:
                if book.is_active:
                    book.is_active = False
                    book.finish_date = datetime.datetime.now()
                    if not detail.get("_book_already_counted_as_updated"):
                        updated_books_count += 1 # Count as updated if status changed
                        detail["_book_already_counted_as_updated"] = True
                    print(f"Book {book.book_number} (Shift {shift_id}) deactivated after sales processing.")
                elif not book.finish_date:
                    book.finish_date = datetime.datetime.now()

        return successful_sales_count, updated_books_count, error_messages