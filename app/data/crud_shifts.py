import datetime
from typing import List, Optional

from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, desc

from app.core.models import ShiftSubmission, SalesEntry, User, Book  # Ensure all are imported
from app.core.exceptions import DatabaseError # Add if specific exceptions are raised

def create_shift_submission(
        db: Session,
        user_id: int,
        submission_dt: datetime.datetime,
        reported_online_sales_float: float,       # Expect float (dollars.cents)
        reported_online_payouts_float: float,     # Expect float
        reported_instant_payouts_float: float,    # Expect float
        actual_cash_in_drawer_float: float        # Expect float
) -> ShiftSubmission:
    """
    Creates a new ShiftSubmission instance.
    Converts float monetary inputs (dollars.cents) to integer cents for storage.
    Calculates delta values based on previous shifts on the same calendar_date.
    Calculates calculated_drawer_value and drawer_difference.
    Initializes aggregates for instant sales to 0; these are updated later.
    Does NOT commit the transaction.
    """
    calendar_date = submission_dt.date()

    # Convert float inputs to cents (integers) for model storage and calculations
    reported_online_sales_cents = int(reported_online_sales_float * 100)
    reported_online_payouts_cents = int(reported_online_payouts_float * 100)
    reported_instant_payouts_cents = int(reported_instant_payouts_float * 100)
    actual_cash_in_drawer_cents = int(actual_cash_in_drawer_float * 100)

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
    current_delta_online_sales_cents = reported_online_sales_cents - previous_online_sales_deltas_sum_cents
    current_delta_online_payouts_cents = reported_online_payouts_cents - previous_online_payouts_deltas_sum_cents
    current_delta_instant_payouts_cents = reported_instant_payouts_cents - previous_instant_payouts_deltas_sum_cents

    shift = ShiftSubmission(
        user_id=user_id,
        submission_datetime=submission_dt,
        calendar_date=calendar_date,
        reported_total_online_sales_today=reported_online_sales_cents,
        reported_total_online_payouts_today=reported_online_payouts_cents,
        reported_total_instant_payouts_today=reported_instant_payouts_cents,
        calculated_delta_online_sales=current_delta_online_sales_cents,
        calculated_delta_online_payouts=current_delta_online_payouts_cents,
        calculated_delta_instant_payouts=current_delta_instant_payouts_cents,
        total_tickets_sold_instant=0, # Default, will be updated (count)
        total_value_instant=0,        # Default, will be updated (dollars, from SalesEntry)
        calculated_drawer_value=0,    # Default, will be updated (cents)
        drawer_difference=0           # Default, will be set based on calculated_drawer_value and actual_cash
    )

    # Initial calculation of calculated_drawer_value (in cents)
    # total_value_instant is in DOLLARS, so convert to cents for this calculation
    # This will be recalculated more accurately in update_shift_aggregates_and_drawer_value
    # after instant sales are processed.
    # For now, it's 0. The main calculation happens in the update function.

    # Initial calculation of drawer_difference (in cents)
    # This also relies on calculated_drawer_value which will be finalized later.
    # The final drawer_difference will be:
    # shift.calculated_drawer_value (after update) - actual_cash_in_drawer_cents
    # We can set an initial drawer_difference here if needed, or let update_shift_aggregates_and_drawer_value handle it.
    # For now, let's set it based on the current (likely zero) calculated_drawer_value.
    # It will be effectively re-set once calculated_drawer_value is finalized.

    # The actual_cash_in_drawer_cents is fixed at this point.
    # The calculated_drawer_value will be updated.
    # So, drawer_difference should be set in update_shift_aggregates_and_drawer_value
    # by passing actual_cash_in_drawer_cents to it, or by storing actual_cash on shift (less ideal).
    # Let's defer final drawer_difference calculation to update_shift_aggregates_and_drawer_value.
    # To do this, we'll pass actual_cash_in_drawer_cents to it.

    print(f"DEBUG CRUD Create Shift: User {user_id}, Reported Online Sales (cents): {reported_online_sales_cents}")
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
        actual_cash_in_drawer_cents: Optional[int] = None # Pass this for new shifts
) -> ShiftSubmission:
    """
    Recalculates instant sales aggregates, calculated_drawer_value, and drawer_difference for a given shift.
    Assumes sales_entries for the shift are already in the session and will be summed.
    `total_value_instant` (from SalesEntry) is in DOLLARS.
    All other monetary values on ShiftSubmission are in CENTS.
    """
    if not shift:
        raise ValueError("Shift object cannot be None for updating aggregates.")

    if shift.id is None:
        total_tickets_sold_instant_agg = 0
        total_value_instant_dollars_agg = 0 # SalesEntry.price is in dollars
    else:
        aggregates = db.query(
            func.sum(SalesEntry.count).label("total_tickets"),
            func.sum(SalesEntry.price).label("total_value") # This sum is in DOLLARS
        ).filter(SalesEntry.shift_id == shift.id).one()

        total_tickets_sold_instant_agg = aggregates.total_tickets or 0
        total_value_instant_dollars_agg = aggregates.total_value or 0 # This is in DOLLARS

    shift.total_tickets_sold_instant = total_tickets_sold_instant_agg
    shift.total_value_instant = total_value_instant_dollars_agg # Store in DOLLARS as per model

    # Recalculate calculated_drawer_value (in CENTS)
    # shift.total_value_instant is in DOLLARS, convert to CENTS for this calculation
    # Other shift fields (deltas) are already in CENTS.
    calculated_drawer_value_cents = (
            shift.calculated_delta_online_sales +
            (shift.total_value_instant * 100) -  # Convert instant sales dollars to cents
            (shift.calculated_delta_online_payouts + shift.calculated_delta_instant_payouts)
    )
    shift.calculated_drawer_value = calculated_drawer_value_cents

    # If actual_cash_in_drawer_cents is provided (for new shifts), calculate drawer_difference
    if actual_cash_in_drawer_cents is not None:
        shift.drawer_difference = calculated_drawer_value_cents - actual_cash_in_drawer_cents
    # Else (for existing shifts being recalculated for other reasons, or admin shifts),
    # drawer_difference might be managed differently or assumed to be pre-set (e.g., to 0 for admin).

    print(f"DEBUG CRUD Update Shift: ID {shift.id} - Instant Sales Agg: Tickets={shift.total_tickets_sold_instant}, Value (Stored Dollars)={shift.total_value_instant}")
    print(f"DEBUG CRUD Update Shift: ID {shift.id} - Deltas (Cents): OnlineSales={shift.calculated_delta_online_sales}, OnlinePayouts={shift.calculated_delta_online_payouts}, InstantPayouts={shift.calculated_delta_instant_payouts}")
    print(f"DEBUG CRUD Update Shift: ID {shift.id} - Calculated Drawer Value (Cents): {shift.calculated_drawer_value}")
    if actual_cash_in_drawer_cents is not None:
        print(f"DEBUG CRUD Update Shift: ID {shift.id} - Actual Cash (Cents): {actual_cash_in_drawer_cents}, Drawer Difference (Cents): {shift.drawer_difference}")

    return shift