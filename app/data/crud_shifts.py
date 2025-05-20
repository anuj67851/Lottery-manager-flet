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
        reported_online_sales: int,
        reported_online_payouts: int,
        reported_instant_payouts: int
) -> ShiftSubmission:
    """
    Creates a new ShiftSubmission instance.
    Calculates delta values based on previous shifts on the same calendar_date.
    Initializes aggregates to 0; these are updated later.
    Does NOT commit the transaction.
    """
    calendar_date = submission_dt.date()

    # Calculate previous delta sums for the same calendar_date
    # Ensure filtering by submission_datetime < current submission_dt to avoid including itself in sums
    # Also, filter by calendar_date to only consider shifts from the same day.

    previous_online_sales_deltas_sum = db.query(func.sum(ShiftSubmission.calculated_delta_online_sales)).filter(
        ShiftSubmission.calendar_date == calendar_date,
        ShiftSubmission.submission_datetime < submission_dt
    ).scalar() or 0

    previous_online_payouts_deltas_sum = db.query(func.sum(ShiftSubmission.calculated_delta_online_payouts)).filter(
        ShiftSubmission.calendar_date == calendar_date,
        ShiftSubmission.submission_datetime < submission_dt
    ).scalar() or 0

    previous_instant_payouts_deltas_sum = db.query(func.sum(ShiftSubmission.calculated_delta_instant_payouts)).filter(
        ShiftSubmission.calendar_date == calendar_date,
        ShiftSubmission.submission_datetime < submission_dt
    ).scalar() or 0

    # Calculate current deltas
    current_delta_online_sales = reported_online_sales - previous_online_sales_deltas_sum
    current_delta_online_payouts = reported_online_payouts - previous_online_payouts_deltas_sum
    current_delta_instant_payouts = reported_instant_payouts - previous_instant_payouts_deltas_sum

    shift = ShiftSubmission(
        user_id=user_id,
        submission_datetime=submission_dt,
        calendar_date=calendar_date, # Already derived
        reported_total_online_sales_today=reported_online_sales,
        reported_total_online_payouts_today=reported_online_payouts,
        reported_total_instant_payouts_today=reported_instant_payouts,
        calculated_delta_online_sales=current_delta_online_sales,
        calculated_delta_online_payouts=current_delta_online_payouts,
        calculated_delta_instant_payouts=current_delta_instant_payouts,
        total_tickets_sold_instant=0, # Default, will be updated
        total_value_instant=0,        # Default, will be updated
        net_drop_value=0              # Default, will be updated
    )

    print(f"DEBUG: Calendar Date: {calendar_date}")
    print(f"DEBUG: Submission DT: {submission_dt}")
    print(f"DEBUG: Reported Online Sales: {reported_online_sales}, Prev Sum: {previous_online_sales_deltas_sum}, Current Delta: {current_delta_online_sales}")
    # db.add(shift) # The service layer will add to session
    return shift

def get_shift_by_id(db: Session, shift_id: int) -> Optional[ShiftSubmission]:
    """Retrieves a shift by ID, optionally eager loading related user and sales_entries."""
    return db.query(ShiftSubmission).options(
        selectinload(ShiftSubmission.user), # Eager load user
        selectinload(ShiftSubmission.sales_entries).joinedload(SalesEntry.book).joinedload(Book.game) # Eager load sales entries -> book -> game
    ).filter(ShiftSubmission.id == shift_id).first()

def get_shifts_by_user_and_date_range(
        db: Session,
        user_id: Optional[int],
        start_date: datetime.datetime, # Should be datetime to compare with submission_datetime accurately
        end_date: datetime.datetime   # Should be datetime
) -> List[ShiftSubmission]:
    """
    Retrieves shifts for a given user (optional) and date range (inclusive for submission_datetime).
    Ordered by submission_datetime descending.
    """
    query = db.query(ShiftSubmission).options(
        selectinload(ShiftSubmission.user),
        selectinload(ShiftSubmission.sales_entries) # Load sales entries as well for reporting
    )

    # Ensure end_date captures the entire day if only date part is provided
    # This logic is better handled in the service/view layer before calling CRUD

    query = query.filter(ShiftSubmission.submission_datetime >= start_date)
    query = query.filter(ShiftSubmission.submission_datetime <= end_date)

    if user_id is not None:
        query = query.filter(ShiftSubmission.user_id == user_id)

    return query.order_by(desc(ShiftSubmission.submission_datetime)).all()


def update_shift_instant_aggregates_and_drop(db: Session, shift: ShiftSubmission) -> ShiftSubmission:
    """
    Recalculates instant sales aggregates and net_drop_value for a given shift.
    Assumes sales_entries for the shift are already in the session and will be summed.
    """
    if not shift:
        raise ValueError("Shift object cannot be None for updating aggregates.")

    # Sum 'count' and 'price' from SalesEntry records associated with this shift
    # This requires that sales_entries relationship is populated or entries are queryable via shift.id

    # If shift.sales_entries is already populated (e.g., due to flush and relationships):
    # total_tickets = sum(entry.count for entry in shift.sales_entries if entry.count is not None)
    # total_value = sum(entry.price for entry in shift.sales_entries if entry.price is not None)

    # More robust: Query the aggregates directly from the DB based on shift.id
    # This ensures we get the correct sum even if shift.sales_entries isn't fully up-to-date in memory
    # or if there are many entries.

    if shift.id is None: # Should not happen if shift was flushed
        # If ID is None, aggregates remain 0 as no entries can be linked yet.
        # This path is unlikely if called after shift creation and sales_entry processing.
        total_tickets = 0
        total_value = 0
    else:
        aggregates = db.query(
            func.sum(SalesEntry.count).label("total_tickets"),
            func.sum(SalesEntry.price).label("total_value")
        ).filter(SalesEntry.shift_id == shift.id).one() # Use .one() as we expect one row of aggregates

        total_tickets = aggregates.total_tickets or 0
        total_value = aggregates.total_value or 0

    shift.total_tickets_sold_instant = total_tickets
    shift.total_value_instant = total_value

    # Recalculate net_drop_value
    shift.net_drop_value = (
            shift.calculated_delta_online_sales +
            shift.total_value_instant -
            (shift.calculated_delta_online_payouts + shift.calculated_delta_instant_payouts)
    )

    # In crud_shifts.update_shift_instant_aggregates_and_drop
    print(f"DEBUG: Shift ID {shift.id} - Aggregates from SalesEntry: Tickets={total_tickets}, Value={total_value}")
    print(f"DEBUG: Shift ID {shift.id} - Deltas for Net Drop: OnlineSales={shift.calculated_delta_online_sales}, OnlinePayouts={shift.calculated_delta_online_payouts}, InstantPayouts={shift.calculated_delta_instant_payouts}")
    print(f"DEBUG: Shift ID {shift.id} - Calculated Net Drop: {shift.net_drop_value}")

    # db.add(shift) # Shift is already in session, changes will be picked up by commit
    return shift