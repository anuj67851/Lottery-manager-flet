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
        Calculates aggregates for this special shift. Drawer difference will be $0.
        """
        current_submission_datetime = datetime.datetime.now()
        created_shift = None
        successful_sales_count = 0
        error_messages: List[str] = []

        try:
            calendar_date = current_submission_datetime.date()

            previous_online_sales_deltas_sum_cents = db.query(func.sum(ShiftSubmission.calculated_delta_online_sales)).filter(
                ShiftSubmission.calendar_date == calendar_date,
                ShiftSubmission.submission_datetime < current_submission_datetime
            ).scalar() or 0

            previous_online_payouts_deltas_sum_cents = db.query(func.sum(ShiftSubmission.calculated_delta_online_payouts)).filter(
                ShiftSubmission.calendar_date == calendar_date,
                ShiftSubmission.submission_datetime < current_submission_datetime
            ).scalar() or 0

            previous_instant_payouts_deltas_sum_cents = db.query(func.sum(ShiftSubmission.calculated_delta_instant_payouts)).filter(
                ShiftSubmission.calendar_date == calendar_date,
                ShiftSubmission.submission_datetime < current_submission_datetime
            ).scalar() or 0

            # For admin shifts, actual cash is assumed to match calculated, so difference is 0.
            # We pass 0.0 initially for actual_cash_in_drawer_float; drawer_difference will be set to 0 explicitly later.
            created_shift = crud_shifts.create_shift_submission(
                db=db,
                user_id=admin_user_id,
                submission_dt=current_submission_datetime,
                reported_online_sales_float=previous_online_sales_deltas_sum_cents / 100.0, # Convert cents to float dollars
                reported_online_payouts_float=previous_online_payouts_deltas_sum_cents / 100.0,
                reported_instant_payouts_float=previous_instant_payouts_deltas_sum_cents / 100.0,
                actual_cash_in_drawer_float=0.0 # Placeholder, will result in drawer_difference = 0
            )
            db.add(created_shift)
            db.flush()  # Get created_shift.id

            book_service = BookService()

            for book_id in book_ids_to_sell:
                try:
                    book_model = book_service.get_book_by_id(db, book_id)
                    if not book_model:
                        raise BookNotFoundError(f"Book ID {book_id} not found.")
                    if not book_model.game:
                        db.refresh(book_model, ['game'])

                    book_service.mark_book_as_fully_sold(db, book_model.id)
                    self.sales_entry_service.create_sales_entry_for_full_book(
                        db, book_model, created_shift.id
                    )
                    successful_sales_count += 1
                except (BookNotFoundError, DatabaseError, Exception) as e_book_sale:
                    error_messages.append(f"Book ID {book_id}: {str(e_book_sale)}")

            db.flush()

            # Update aggregates. For admin shifts, actual_cash_in_drawer is effectively the calculated_drawer_value.
            # The `actual_cash_in_drawer_cents` parameter for update_shift_aggregates_and_drawer_value
            # is not strictly needed here because we will override drawer_difference.
            # However, to keep the CRUD function simpler, we can pass the calculated value.

            crud_shifts.update_shift_aggregates_and_drawer_value(db, created_shift, actual_cash_in_drawer_cents=None) # Calculate aggregates and calculated_drawer_value

            # For admin "full book sale" shifts, drawer_difference is explicitly $0.
            # The actual_cash_in_drawer would be equal to created_shift.calculated_drawer_value.
            created_shift.drawer_difference = 0

            # db.commit() is handled by caller

            return created_shift, successful_sales_count, error_messages

        except Exception as e_main:
            error_messages.append(f"Critical error during admin full book sale processing: {str(e_main)}")
            return created_shift, successful_sales_count, error_messages

    def create_new_shift_submission(
            self,
            db: Session,
            user_id: int,
            reported_online_sales_float: float,    # Expect float (dollars.cents)
            reported_online_payouts_float: float,  # Expect float
            reported_instant_payouts_float: float, # Expect float
            actual_cash_in_drawer_float: float,    # Expect float
            sales_item_details: List[Dict[str, Any]]
    ) -> ShiftSubmission:
        """
        Coordinates the creation of a new shift submission.
        Float monetary inputs are converted to cents in the CRUD layer.
        """
        current_submission_datetime = datetime.datetime.now()

        shift_obj = crud_shifts.create_shift_submission(
            db=db,
            user_id=user_id,
            submission_dt=current_submission_datetime,
            reported_online_sales_float=reported_online_sales_float,
            reported_online_payouts_float=reported_online_payouts_float,
            reported_instant_payouts_float=reported_instant_payouts_float,
            actual_cash_in_drawer_float=actual_cash_in_drawer_float
        )
        db.add(shift_obj)
        db.flush()  # Get shift_obj.id

        if sales_item_details:
            _successful_sales_count, _updated_books_count, sales_processing_errors = \
                self.sales_entry_service.process_and_save_sales_batch_for_shift(
                    db=db,
                    shift_id=shift_obj.id,
                    sales_item_details=sales_item_details
                )
            db.flush()
            if sales_processing_errors:
                print(f"ShiftService: Errors during sales entry processing for shift {shift_obj.id}: {sales_processing_errors}")

        # Pass actual_cash_in_drawer_cents to the update function so it can set drawer_difference
        actual_cash_in_drawer_cents = int(actual_cash_in_drawer_float * 100)
        updated_shift_obj = crud_shifts.update_shift_aggregates_and_drawer_value(
            db, shift_obj, actual_cash_in_drawer_cents
        )

        # db.commit() will be handled by the get_db_session context manager

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