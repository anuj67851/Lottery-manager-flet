import datetime
import logging
from typing import List, Optional

from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, desc

from app.core.models import ShiftSubmission, SalesEntry, User, Book
from app.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)
def create_shift_submission(
        db: Session,
        user_id: int,
        submission_dt: datetime.datetime,
        # Dollar float inputs (primarily for employee shifts from UI)
        reported_online_sales_float: Optional[float] = None,
        reported_online_payouts_float: Optional[float] = None,
        reported_instant_payouts_float: Optional[float] = None,
        actual_cash_in_drawer_float: Optional[float] = None, # Still needed for employee shifts
        # Cent integer inputs (primarily for system-derived values like admin shifts)
        reported_total_online_sales_today_cents_input: Optional[int] = None,
        reported_total_online_payouts_today_cents_input: Optional[int] = None,
        reported_total_instant_payouts_today_cents_input: Optional[int] = None
) -> ShiftSubmission:
    """
    Creates a new ShiftSubmission instance.
    Preferentially uses _cents_input parameters if provided for reported totals.
    Otherwise, converts float monetary inputs (dollars.cents) to integer cents.
    Calculates delta values based on previous shifts on the same calendar_date.
    `total_value_instant` will be stored in CENTS.
    Does NOT commit the transaction.
    """
    calendar_date = submission_dt.date()

    # Determine reported total values in cents
    if reported_total_online_sales_today_cents_input is not None:
        final_reported_online_sales_cents = reported_total_online_sales_today_cents_input
    elif reported_online_sales_float is not None:
        final_reported_online_sales_cents = int(round(reported_online_sales_float * 100))
    else:
        raise ValueError("Either reported_online_sales_float or reported_total_online_sales_today_cents_input must be provided.")

    if reported_total_online_payouts_today_cents_input is not None:
        final_reported_online_payouts_cents = reported_total_online_payouts_today_cents_input
    elif reported_online_payouts_float is not None:
        final_reported_online_payouts_cents = int(round(reported_online_payouts_float * 100))
    else:
        raise ValueError("Either reported_online_payouts_float or reported_total_online_payouts_today_cents_input must be provided.")

    if reported_total_instant_payouts_today_cents_input is not None:
        final_reported_instant_payouts_cents = reported_total_instant_payouts_today_cents_input
    elif reported_instant_payouts_float is not None:
        final_reported_instant_payouts_cents = int(round(reported_instant_payouts_float * 100))
    else:
        raise ValueError("Either reported_instant_payouts_float or reported_total_instant_payouts_today_cents_input must be provided.")

    # Calculate previous delta sums for the same calendar_date (values are already in cents in DB)
    previous_online_sales_deltas_sum_cents = db.query(func.sum(ShiftSubmission.calculated_delta_online_sales)).filter(
        ShiftSubmission.calendar_date == calendar_date,
        ShiftSubmission.submission_datetime < submission_dt
    ).scalar() or 0

    previous_online_payouts_deltas_sum_cents = db.query(func.sum(ShiftSubmission.calculated_delta_online_payouts)).filter(
        ShiftSubmission.calendar_date == calendar_date,
        ShiftSubmission.submission_datetime < submission_dt
    ).scalar() or 0

    previous_instant_payouts_deltas_sum_cents = db.query(func.sum(ShiftSubmission.calculated_delta_instant_payouts)).filter(
        ShiftSubmission.calendar_date == calendar_date,
        ShiftSubmission.submission_datetime < submission_dt
    ).scalar() or 0

    # Calculate current deltas (in cents)
    current_delta_online_sales_cents = final_reported_online_sales_cents - previous_online_sales_deltas_sum_cents
    current_delta_online_payouts_cents = final_reported_online_payouts_cents - previous_online_payouts_deltas_sum_cents
    current_delta_instant_payouts_cents = final_reported_instant_payouts_cents - previous_instant_payouts_deltas_sum_cents

    shift = ShiftSubmission(
        user_id=user_id,
        submission_datetime=submission_dt,
        calendar_date=calendar_date,
        reported_total_online_sales_today=final_reported_online_sales_cents,
        reported_total_online_payouts_today=final_reported_online_payouts_cents,
        reported_total_instant_payouts_today=final_reported_instant_payouts_cents,
        calculated_delta_online_sales=current_delta_online_sales_cents,
        calculated_delta_online_payouts=current_delta_online_payouts_cents,
        calculated_delta_instant_payouts=current_delta_instant_payouts_cents,
        total_tickets_sold_instant=0,
        total_value_instant=0, # CENTS
        calculated_drawer_value=0,
        drawer_difference=0
    )

    # actual_cash_in_drawer_float is still needed for regular shifts to be passed to update_shift_aggregates_and_drawer_value
    # This CRUD function doesn't use it directly for setting drawer_difference.
    # The service layer passes the converted actual_cash_in_drawer_cents to the update function.

    logger.debug(f"DEBUG CRUD Create Shift: User {user_id}, Reported Online Sales (cents): {final_reported_online_sales_cents}")
    return shift

def get_shift_by_id(db: Session, shift_id: int) -> Optional[ShiftSubmission]:
    """Retrieves a shift by ID, optionally eager loading related user and sales_entries."""
    return db.query(ShiftSubmission).options(
        selectinload(ShiftSubmission.user),
        selectinload(ShiftSubmission.sales_entries).joinedload(SalesEntry.book).joinedload(Book.game)
    ).filter(ShiftSubmission.id == shift_id).first()

def get_shifts_by_user_and_date_range(
        db: Session,
        user_id: Optional[int],
        start_date: datetime.datetime,
        end_date: datetime.datetime
) -> List[ShiftSubmission]:
    """
    Retrieves shifts for a given user (optional) and date range (inclusive for submission_datetime).
    Ordered by submission_datetime descending.
    """
    query = db.query(ShiftSubmission).options(
        selectinload(ShiftSubmission.user),
        selectinload(ShiftSubmission.sales_entries)
    )

    query = query.filter(ShiftSubmission.submission_datetime >= start_date)
    query = query.filter(ShiftSubmission.submission_datetime <= end_date)

    if user_id is not None:
        query = query.filter(ShiftSubmission.user_id == user_id)

    return query.order_by(desc(ShiftSubmission.submission_datetime)).all()


def update_shift_aggregates_and_drawer_value(
        db: Session,
        shift: ShiftSubmission,
        actual_cash_in_drawer_cents: Optional[int] = None # Pass this for new shifts (in CENTS)
) -> ShiftSubmission:
    """
    Recalculates instant sales aggregates, calculated_drawer_value, and drawer_difference for a given shift.
    Assumes sales_entries for the shift are already in the session and will be summed.
    `SalesEntry.price` is in CENTS.
    `ShiftSubmission.total_value_instant` will store CENTS.
    All other monetary values on ShiftSubmission are in CENTS.
    """
    if not shift:
        raise ValueError("Shift object cannot be None for updating aggregates.")

    total_tickets_sold_instant_agg = 0
    total_value_instant_cents_agg = 0 # SalesEntry.price is in CENTS

    if shift.id is not None:
        aggregates = db.query(
            func.sum(SalesEntry.count).label("total_tickets"),
            func.sum(SalesEntry.price).label("total_value") # This sum is in CENTS
        ).filter(SalesEntry.shift_id == shift.id).one_or_none()

        if aggregates:
            total_tickets_sold_instant_agg = aggregates.total_tickets or 0
            total_value_instant_cents_agg = aggregates.total_value or 0

    shift.total_tickets_sold_instant = total_tickets_sold_instant_agg
    shift.total_value_instant = total_value_instant_cents_agg # Store in CENTS

    calculated_drawer_value_cents = (
            shift.calculated_delta_online_sales +
            shift.total_value_instant - # Already in CENTS
            (shift.calculated_delta_online_payouts + shift.calculated_delta_instant_payouts)
    )
    shift.calculated_drawer_value = calculated_drawer_value_cents

    if actual_cash_in_drawer_cents is not None:
        shift.drawer_difference = calculated_drawer_value_cents - actual_cash_in_drawer_cents

    logger.debug(f"DEBUG CRUD Update Shift: ID {shift.id} - Instant Sales Agg: Tickets={shift.total_tickets_sold_instant}, Value (Stored Cents)={shift.total_value_instant}")
    logger.debug(f"DEBUG CRUD Update Shift: ID {shift.id} - Deltas (Cents): OnlineSales={shift.calculated_delta_online_sales}, OnlinePayouts={shift.calculated_delta_online_payouts}, InstantPayouts={shift.calculated_delta_instant_payouts}")
    logger.debug(f"DEBUG CRUD Update Shift: ID {shift.id} - Calculated Drawer Value (Cents): {shift.calculated_drawer_value}")
    if actual_cash_in_drawer_cents is not None:
        logger.debug(f"DEBUG CRUD Update Shift: ID {shift.id} - Actual Cash (Cents): {actual_cash_in_drawer_cents}, Drawer Difference (Cents): {shift.drawer_difference}")

    return shift