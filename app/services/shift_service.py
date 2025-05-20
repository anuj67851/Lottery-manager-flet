import datetime
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func # Added import

from app.core import BookNotFoundError, DatabaseError
from app.core.models import ShiftSubmission # Assuming ShiftSubmission from models.py
from app.data import crud_shifts
from app.services import BookService
from app.services.sales_entry_service import SalesEntryService # Will be used here

class ShiftService:
    def __init__(self):
        # SalesEntryService might be instantiated here or passed if it has dependencies
        self.sales_entry_service = SalesEntryService()

    def create_shift_for_admin_full_book_sales(
            self,
            db: Session,
            admin_user_id: int,
            book_ids_to_sell: List[int] # List of Book IDs to be marked as fully sold
    ) -> Tuple[ShiftSubmission, int, List[str]]: # Returns created shift, success_count, error_messages
        """
        Creates a dedicated shift for admin-triggered full book sales.
        Marks books as sold and creates corresponding sales entries.
        Calculates aggregates for this special shift.
        """
        current_submission_datetime = datetime.datetime.now()
        created_shift = None
        successful_sales_count = 0
        error_messages: List[str] = []

        try:
            # Determine calendar_date for querying previous shifts
            calendar_date = current_submission_datetime.date()

            # Fetch sum of previous deltas for the same calendar_date to make new deltas zero
            previous_online_sales_deltas_sum = db.query(func.sum(ShiftSubmission.calculated_delta_online_sales)).filter(
                ShiftSubmission.calendar_date == calendar_date,
                ShiftSubmission.submission_datetime < current_submission_datetime
            ).scalar() or 0

            previous_online_payouts_deltas_sum = db.query(func.sum(ShiftSubmission.calculated_delta_online_payouts)).filter(
                ShiftSubmission.calendar_date == calendar_date,
                ShiftSubmission.submission_datetime < current_submission_datetime
            ).scalar() or 0

            previous_instant_payouts_deltas_sum = db.query(func.sum(ShiftSubmission.calculated_delta_instant_payouts)).filter(
                ShiftSubmission.calendar_date == calendar_date,
                ShiftSubmission.submission_datetime < current_submission_datetime
            ).scalar() or 0

            # 1. Create the initial ShiftSubmission for this admin action
            # Pass the fetched sums as reported values. This will result in zero deltas for these attributes.
            created_shift = crud_shifts.create_shift_submission(
                db=db,
                user_id=admin_user_id,
                submission_dt=current_submission_datetime,
                reported_online_sales=previous_online_sales_deltas_sum,
                reported_online_payouts=previous_online_payouts_deltas_sum,
                reported_instant_payouts=previous_instant_payouts_deltas_sum
            )
            db.add(created_shift)
            db.flush()  # Get created_shift.id

            # 2. Process each book for full sale
            book_service = BookService() # Local instance or could be self.book_service if added

            for book_id in book_ids_to_sell:
                try:
                    book_model = book_service.get_book_by_id(db, book_id)
                    if not book_model:
                        raise BookNotFoundError(f"Book ID {book_id} not found.")
                    if not book_model.game: # Ensure game is loaded for SalesEntry calculation
                        db.refresh(book_model, ['game'])

                    # Mark book as fully sold (updates book status, current_ticket_number)
                    book_service.mark_book_as_fully_sold(db, book_model.id)

                    # Create a sales entry for the full book sale, linking to this admin shift
                    self.sales_entry_service.create_sales_entry_for_full_book(
                        db, book_model, created_shift.id
                    )
                    successful_sales_count += 1
                except (BookNotFoundError, DatabaseError, Exception) as e_book_sale:
                    error_messages.append(f"Book ID {book_id}: {str(e_book_sale)}")
                    # Continue processing other books

            db.flush()

            # 3. Update the admin shift's instant aggregates and net_drop_value
            # This must be done *after* all sales entries for this shift are created and flushed.
            crud_shifts.update_shift_instant_aggregates_and_drop(db, created_shift)

            # The transaction commit is handled by the caller (e.g., BookActionDialog's get_db_session)
            return created_shift, successful_sales_count, error_messages

        except Exception as e_main:
            # If shift creation itself fails or another major error before loop
            error_messages.append(f"Critical error during admin full book sale processing: {str(e_main)}")
            # created_shift might be None or partially formed.
            # The transaction rollback (by get_db_session) is crucial here.
            return created_shift, successful_sales_count, error_messages
    def create_new_shift_submission(
            self,
            db: Session,
            user_id: int,
            reported_online_sales: int,
            reported_online_payouts: int,
            reported_instant_payouts: int,
            sales_item_details: List[Dict[str, Any]] # From UI, for instant sales
    ) -> ShiftSubmission:
        """
        Coordinates the creation of a new shift submission, including its sales entries
        and aggregate calculations.
        Operates within a single database transaction managed by the caller (e.g., view using get_db_session).
        """
        current_submission_datetime = datetime.datetime.now()

        # 1. Create the ShiftSubmission object (without sales entries yet)
        # This calculates the deltas based on previous shifts.
        shift_obj = crud_shifts.create_shift_submission(
            db=db,
            user_id=user_id,
            submission_dt=current_submission_datetime,
            reported_online_sales=reported_online_sales,
            reported_online_payouts=reported_online_payouts,
            reported_instant_payouts=reported_instant_payouts
        )
        db.add(shift_obj)
        db.flush()  # Flush to get shift_obj.id for linking sales entries

        # 2. Process and save SalesEntry records for instant games
        # The sales_entry_service method will now take shift_id.
        # It should return counts/errors but not commit or update shift aggregates itself.
        if sales_item_details: # Only process if there are instant sales items
            _successful_sales_count, _updated_books_count, sales_processing_errors = \
                self.sales_entry_service.process_and_save_sales_batch_for_shift(
                    db=db,
                    shift_id=shift_obj.id, # Link to the new shift
                    sales_item_details=sales_item_details
                )

            db.flush()

            # Handle sales_processing_errors if necessary. For now, we assume they might be logged
            # or returned up to the UI layer by a higher-level coordinator if critical.
            # If errors occur here, the transaction will be rolled back by get_db_session.
            if sales_processing_errors:
                # Depending on severity, you might want to raise an exception here
                # to ensure the transaction rolls back and no partial data is saved.
                # For example:
                # raise ValueError(f"Errors occurred during sales entry processing for shift: {sales_processing_errors}")
                print(f"ShiftService: Errors during sales entry processing for shift {shift_obj.id}: {sales_processing_errors}")


        # 3. Update instant sales aggregates and net_drop_value on the ShiftSubmission object
        # This must be done *after* sales entries are created and flushed.
        updated_shift_obj = crud_shifts.update_shift_instant_aggregates_and_drop(db, shift_obj)

        # db.commit() will be handled by the get_db_session context manager in the view/caller.

        return updated_shift_obj

    def get_shifts_for_report(
            self,
            db: Session,
            start_date: datetime.datetime,
            end_date: datetime.datetime,
            user_id: Optional[int] = None
    ) -> List[ShiftSubmission]:
        """
        Retrieves shift submissions for reporting purposes.
        """
        return crud_shifts.get_shifts_by_user_and_date_range(
            db=db,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )