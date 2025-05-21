import datetime
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core import BookNotFoundError, DatabaseError
from app.core.models import ShiftSubmission
from app.data import crud_shifts
from app.services import BookService
from app.services.sales_entry_service import SalesEntryService

class ShiftService:
    def __init__(self):
        self.sales_entry_service = SalesEntryService()

    def create_shift_for_admin_full_book_sales(
            self,
            db: Session,
            admin_user_id: int,
            book_ids_to_sell: List[int]
    ) -> Tuple[ShiftSubmission, int, List[str]]:
        """
        Creates a dedicated shift for admin-triggered full book sales.
        Marks books as sold and creates corresponding sales entries.
        Calculates aggregates for this special shift. Drawer difference will be $0.
        `total_value_instant` will be in CENTS.
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

            # Now directly pass the sums (in cents) to the new _cents_input parameters
            created_shift = crud_shifts.create_shift_submission(
                db=db,
                user_id=admin_user_id,
                submission_dt=current_submission_datetime,
                # Pass cents directly for reported totals for this admin shift
                reported_total_online_sales_today_cents_input=previous_online_sales_deltas_sum_cents,
                reported_total_online_payouts_today_cents_input=previous_online_payouts_deltas_sum_cents,
                reported_total_instant_payouts_today_cents_input=previous_instant_payouts_deltas_sum_cents,
                actual_cash_in_drawer_float=0.0 # Still pass 0.0 for consistency, drawer_difference explicitly set later
            )
            db.add(created_shift)
            db.flush()

            book_service = BookService()
            for book_id in book_ids_to_sell:
                try:
                    book_model = book_service.get_book_by_id(db, book_id)
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

            # actual_cash_in_drawer_cents is effectively the calculated_drawer_value for admin shifts.
            # First calculate aggregates and the drawer value:
            crud_shifts.update_shift_aggregates_and_drawer_value(db, created_shift, actual_cash_in_drawer_cents=None)

            # Then, explicitly set drawer_difference to 0.
            # The calculated_drawer_value (in cents) represents the total value of books sold.
            # We are asserting that the "actual cash" matches this for admin operations.
            created_shift.drawer_difference = 0
            # No need to pass created_shift.calculated_drawer_value to update_shift_aggregates_and_drawer_value
            # as actual_cash_in_drawer_cents, because we directly set drawer_difference = 0.

            return created_shift, successful_sales_count, error_messages

        except Exception as e_main:
            error_messages.append(f"Critical error during admin full book sale processing: {str(e_main)}")
            return created_shift, successful_sales_count, error_messages

    def create_new_shift_submission(
            self,
            db: Session,
            user_id: int,
            reported_online_sales_float: float,
            reported_online_payouts_float: float,
            reported_instant_payouts_float: float,
            actual_cash_in_drawer_float: float,
            sales_item_details: List[Dict[str, Any]]
    ) -> ShiftSubmission:
        current_submission_datetime = datetime.datetime.now()

        # For regular employee shifts, use the _float parameters
        shift_obj = crud_shifts.create_shift_submission(
            db=db,
            user_id=user_id,
            submission_dt=current_submission_datetime,
            reported_online_sales_float=reported_online_sales_float,
            reported_online_payouts_float=reported_online_payouts_float,
            reported_instant_payouts_float=reported_instant_payouts_float,
            actual_cash_in_drawer_float=actual_cash_in_drawer_float # Passed but not used by CRUD for diff directly
        )
        db.add(shift_obj)
        db.flush()

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

        actual_cash_in_drawer_cents = int(round(actual_cash_in_drawer_float * 100))
        updated_shift_obj = crud_shifts.update_shift_aggregates_and_drawer_value(
            db, shift_obj, actual_cash_in_drawer_cents
        )
        return updated_shift_obj

    def get_shifts_for_report(
            self,
            db: Session,
            start_date: datetime.datetime,
            end_date: datetime.datetime,
            user_id: Optional[int] = None
    ) -> List[ShiftSubmission]:
        return crud_shifts.get_shifts_by_user_and_date_range(
            db=db,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )