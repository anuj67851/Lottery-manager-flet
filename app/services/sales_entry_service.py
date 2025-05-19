import datetime
from typing import List, Dict, Tuple, Optional, Any

from sqlalchemy.orm import Session, joinedload

from app.constants import REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER, GAME_LENGTH, BOOK_LENGTH
from app.core.exceptions import ValidationError, DatabaseError, GameNotFoundError
from app.core.models import Book, SalesEntry, Game as GameModel # Added GameModel
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
                # crud_books.create_book correctly initializes current_ticket_number via Book.__init__
                new_book = crud_books.create_book(db, game, book_number_str)
                new_book.is_active = True # Activate new book for sales
                new_book.activate_date = datetime.datetime.now()
                db.flush() # Ensure new_book gets an ID if not committed yet by context manager
                db.refresh(new_book, attribute_names=['game']) # Eager load game for the new book
                print(f"SalesEntryService: Created/activated new book: ID {new_book.id}, Num {new_book.book_number}, Initial Ticket: {new_book.current_ticket_number}")
                return new_book
            except (DatabaseError, ValidationError) as e:
                raise DatabaseError(f"Could not create book {game_number_str}-{book_number_str} for sale: {e.message if hasattr(e, 'message') else e}")
        else: # Book exists
            if not book.game: db.refresh(book, attribute_names=['game']) # Ensure game is loaded
            if not book.is_active:
                # Before activating, ensure the book is not already finished
                if book.ticket_order == REVERSE_TICKET_ORDER and book.current_ticket_number == -1:
                    raise ValidationError(f"Book '{book.book_number}' is already sold out (Reverse). Cannot use for sales.")
                if book.ticket_order == FORWARD_TICKET_ORDER and book.game and book.current_ticket_number == book.game.total_tickets:
                    raise ValidationError(f"Book '{book.book_number}' is already sold out (Forward). Cannot use for sales.")

                book.is_active = True
                book.activate_date = datetime.datetime.now()
                book.finish_date = None # Clear finish date if reactivating
                print(f"SalesEntryService: Activated existing book for sale: {book.book_number}, Current Ticket: {book.current_ticket_number}")
            return book

    def create_sales_entry_for_full_book(self, db: Session, book: Book, user_id: int) -> SalesEntry:
        """
        Creates a SalesEntry record for a book that has been marked as fully sold.
        Assumes the book's current_ticket_number and status have already been updated
        by BookService.mark_book_as_fully_sold.
        """
        if not book.game:
            raise DatabaseError(f"Book ID {book.id} is missing game data for full sale entry.")

        # Determine start_number (state before this "full sale" action)
        # This is tricky if the book was partially sold before.
        # For simplicity, if we are calling this, we assume the "start" was its original pristine state.
        original_start_number = 0
        if book.ticket_order == REVERSE_TICKET_ORDER:
            original_start_number = book.game.total_tickets -1 # Highest ticket number index
        else: # FORWARD_TICKET_ORDER
            original_start_number = 0 # Lowest ticket number index (first to be sold)

        # end_number is the state *after* this "full sale" action
        final_end_number = book.current_ticket_number # This should be -1 or total_tickets

        sales_entry = SalesEntry(
            book_id=book.id,
            user_id=user_id,
            start_number=original_start_number, # Representing the sale of ALL tickets from initial state
            end_number=final_end_number,         # Representing the final state after all tickets sold
            date=datetime.datetime.now(),
            book=book # Associate for calculation
        )
        sales_entry.calculate_count_and_price()

        if sales_entry.count != book.game.total_tickets:
            # This might indicate an issue or an edge case not handled by original_start_number logic.
            # For now, log a warning. The calculation should make count = total_tickets.
            print(f"Warning: Full book sale for Book ID {book.id} resulted in count {sales_entry.count}, expected {book.game.total_tickets}.")
            # Override count if necessary, though calculate_count_and_price should be robust.
            # sales_entry.count = book.game.total_tickets
            # sales_entry.price = sales_entry.count * book.game.price

        return crud_sales_entries.create_sales_entry(db, sales_entry)


    def process_and_save_sales_batch(
            self, db: Session, user_id: int, sales_item_details: List[Dict[str, Any]]
    ) -> Tuple[int, int, List[str]]:
        successful_sales_count = 0
        updated_books_count = 0
        error_messages: List[str] = []

        for detail_idx, detail in enumerate(sales_item_details):
            book_id = detail.get("book_db_id")
            book_state_at_ui_load = detail.get("db_current_ticket_no") # This is crucial
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
            elif ui_target_state_str is not None and (ui_target_state_str == "-1" or ui_target_state_str.isdigit()): # Allow -1
                try:
                    parsed_num = int(ui_target_state_str)
                    # Validate range based on book's order and current state *before* this specific sale transaction.
                    # The book_state_at_ui_load is the book.current_ticket_number *before* this sale.
                    is_range_ok = False
                    if book.ticket_order == REVERSE_TICKET_ORDER:
                        # Can go from book_state_at_ui_load down to -1.
                        # parsed_num must be <= book_state_at_ui_load AND >= -1.
                        is_range_ok = (-1 <= parsed_num <= book_state_at_ui_load)
                    else: # FORWARD_TICKET_ORDER
                        # Can go from book_state_at_ui_load up to total_tickets.
                        # parsed_num must be >= book_state_at_ui_load AND <= book.game.total_tickets.
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

            # For SalesEntry: start_number is book's state before this sale, end_number is book's state after this sale.
            sales_entry_start_number = book_state_at_ui_load
            sales_entry_end_number = final_book_ticket_number_to_set

            calculated_tickets_for_this_entry = 0
            if book.ticket_order == REVERSE_TICKET_ORDER:
                if sales_entry_start_number >= sales_entry_end_number:
                    calculated_tickets_for_this_entry = sales_entry_start_number - sales_entry_end_number
            else: # FORWARD_TICKET_ORDER
                if sales_entry_end_number >= sales_entry_start_number:
                    calculated_tickets_for_this_entry = sales_entry_end_number - sales_entry_start_number

            if calculated_tickets_for_this_entry < 0:
                error_messages.append(f"Item {detail_idx+1}: Negative sales calc for Book {book.book_number}. Start: {sales_entry_start_number}, End: {sales_entry_end_number}. Skipped.")
                continue

            if calculated_tickets_for_this_entry > 0 or all_sold_confirmed_by_ui : # Only create entry if actual sales or explicit all_sold
                try:
                    new_sales_entry = SalesEntry(
                        book_id=book.id, user_id=user_id,
                        start_number=sales_entry_start_number,
                        end_number=sales_entry_end_number,
                        date=datetime.datetime.now(), book=book
                    )
                    new_sales_entry.calculate_count_and_price()

                    if new_sales_entry.count != calculated_tickets_for_this_entry:
                        print(f"Warning: Discrepancy in tickets for Book {book.book_number}. Service: {calculated_tickets_for_this_entry}, Model: {new_sales_entry.count}. Using Model.")

                    if new_sales_entry.count >= 0 : # Allow 0 count sales if 'all_sold' was confirmed for an already finished book
                        crud_sales_entries.create_sales_entry(db, new_sales_entry)
                        successful_sales_count += 1
                    elif new_sales_entry.count < 0: # Should be prevented by earlier checks
                        error_messages.append(f"Item {detail_idx+1}: SalesEntry model calculated negative count for Book {book.book_number}. Skipped sales record.")
                        continue # Skip sales record but still update book below if needed

                except Exception as e_sales:
                    error_messages.append(f"Item {detail_idx+1}: Error creating sales entry for Book {book.book_number}: {e_sales}")
                    continue # If sales entry fails, maybe don't update book? Or make it configurable. For now, continue.

            # Update Book state based on final_book_ticket_number_to_set
            try:
                book.current_ticket_number = final_book_ticket_number_to_set
                updated_books_count += 1 # Count as updated even if only current_ticket_number changed

                is_book_finished_after_this_sale = False
                if book.ticket_order == REVERSE_TICKET_ORDER and final_book_ticket_number_to_set == -1:
                    is_book_finished_after_this_sale = True
                elif book.ticket_order == FORWARD_TICKET_ORDER and final_book_ticket_number_to_set == book.game.total_tickets:
                    is_book_finished_after_this_sale = True

                if all_sold_confirmed_by_ui or is_book_finished_after_this_sale:
                    if book.is_active: # Only deactivate if it was active
                        book.is_active = False
                        book.finish_date = datetime.datetime.now()
                        print(f"Book {book.book_number} deactivated after sales processing.")
                    # If it's already inactive but we confirm all_sold, ensure finish_date is set
                    elif not book.finish_date :
                        book.finish_date = datetime.datetime.now()


            except Exception as e_book:
                error_messages.append(f"Item {detail_idx+1}: Error updating Book {book.book_number} state: {e_book}")

        return successful_sales_count, updated_books_count, error_messages