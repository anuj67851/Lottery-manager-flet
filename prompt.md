**Prompt for AI: Implement Shift Submission & Delta Calculation Feature**

**Instruction to AI:** *Please implement the following feature. Due to its complexity, break down your response and implementation steps into several messages. Address each major section (Database Models, CRUD Layer, Service Layer, UI Layer, etc.) in a separate message or a series of closely related messages. Confirm understanding of each part before proceeding if necessary.*

**Overall Goal:**
Introduce a "Shift Submission" system. Sales entries will be associated with a specific submission event, which is tied to a user. The system must calculate deltas for online sales, online payouts, and instant payouts based on user-reported cumulative daily totals from an external system. This change impacts data models, services, the sales entry UI, and reporting.

**I. Database Model Changes (`app/core/models.py`):**

1.  **New `Shift` Model (or `ShiftSubmission` if you prefer for clarity):**
    This model represents a single instance of a user submitting their sales data and related financial figures for a period.

    *   **Fields for `Shift` Model:**
        *   `id` (Integer, primary_key=True, index=True, autoincrement=True)
        *   `user_id` (Integer, ForeignKey("users.id"), nullable=False, index=True)
        *   `submission_datetime` (DateTime, nullable=False, default=datetime.datetime.now, index=True) - *Timestamp of when this set of data was submitted.*
        *   `calendar_date` (Date, nullable=False, index=True) - *The calendar date this submission pertains to. Derived from `submission_datetime` at creation.*

        *   **User-Reported Cumulative Daily Values (as entered by the user from their terminal):**
            *   `reported_total_online_sales_today` (Integer, nullable=False) - *The total online sales for the `calendar_date` as reported by the user's terminal at the time of this submission.*
            *   `reported_total_online_payouts_today` (Integer, nullable=False) - *The total online payouts for the `calendar_date` as reported by the user's terminal.*
            *   `reported_total_instant_payouts_today` (Integer, nullable=False) - *The total instant payouts for the `calendar_date` as reported by the user's terminal.*

        *   **Calculated Delta Values (for THIS Shift Submission period):**
            *   `calculated_delta_online_sales` (Integer, nullable=False) - *Online sales attributable specifically to this user's submission period. Formula: `reported_total_online_sales_today` MINUS (sum of `calculated_delta_online_sales` from *previous* `Shift` records on the same `calendar_date` for *any user*).*
            *   `calculated_delta_online_payouts` (Integer, nullable=False) - *Online payouts attributable specifically to this submission. Calculated similarly.*
            *   `calculated_delta_instant_payouts` (Integer, nullable=False) - *Instant payouts attributable specifically to this submission. Calculated similarly.*

        *   **Instant Sales Aggregates (from `SalesEntry` records linked to THIS shift):**
            *   `total_tickets_sold_instant` (Integer, nullable=False, default=0) - *Aggregated from linked `SalesEntry` records.*
            *   `total_value_instant` (Integer, nullable=False, default=0) - *Aggregated from linked `SalesEntry` records.*

        *   **Calculated Drop for THIS Shift Submission:**
            *   `net_drop_value` (Integer, nullable=False) - *Calculated as: `calculated_delta_online_sales + total_value_instant - (calculated_delta_online_payouts + calculated_delta_instant_payouts)`.*

        *   `created_date` (DateTime, nullable=False, default=datetime.datetime.now) *(Standard record creation timestamp)*

    *   **Relationships:**
        *   `user` (relationship to `User`, back_populates="shifts")
        *   `sales_entries` (relationship to `SalesEntry`, back_populates="shift", cascade="all, delete-orphan")

    *   **Representation:** Add a `__repr__` method.
    *   **Constraints/Indexes:** Ensure appropriate indexes on `user_id`, `submission_datetime`, and `calendar_date`.

2.  **Modify `User` Model:**
    *   Add/Update the `shifts` relationship to `Shift` (back_populates="user").
        ```python
        # In User model
        shifts = relationship("Shift", back_populates="user", order_by="Shift.submission_datetime.desc()")
        ```

3.  **Modify `SalesEntry` Model:**
    *   **Remove:** `user_id` column and `user` relationship.
    *   **Add/Ensure:**
        *   `shift_id` (Integer, ForeignKey("shifts.id"), nullable=False, index=True)
        *   `shift` (relationship to `Shift`, back_populates="sales_entries")
    *   Update `__repr__` method.

**II. CRUD Layer Changes:**

1.  **New `app/data/crud_shifts.py`:**
    *   `create_shift_submission(db: Session, user_id: int, submission_dt: datetime, reported_online_sales: int, reported_online_payouts: int, reported_instant_payouts: int) -> Shift`:
        *   Derive `calendar_date` from `submission_dt`.
        *   Calculate `calculated_delta_online_sales`, `calculated_delta_online_payouts`, `calculated_delta_instant_payouts`. This requires querying previous `Shift` records for the same `calendar_date` to sum their respective `calculated_delta_...` values.
            *   Example for `calculated_delta_online_sales`:
                ```python
                previous_deltas_sum = db.query(func.sum(Shift.calculated_delta_online_sales)).filter(Shift.calendar_date == calendar_date, Shift.submission_datetime < submission_dt).scalar() or 0
                current_delta_online_sales = reported_online_sales - previous_deltas_sum
                ```
        *   Initialize `total_tickets_sold_instant` and `total_value_instant` to 0.
        *   Initialize `net_drop_value` to 0 (will be updated after sales entries).
        *   Create and return the `Shift` object (but don't commit yet, let the service layer handle the transaction).
    *   `get_shift_by_id(db: Session, shift_id: int) -> Optional[Shift]`: Retrieves a shift by ID, ideally with user and sales_entries eager loaded if frequently accessed together.
    *   `get_shifts_by_user_and_date_range(db: Session, user_id: Optional[int], start_date: datetime, end_date: datetime) -> List[Shift]`: For reporting, ordered by `submission_datetime`.
    *   `update_shift_instant_aggregates_and_drop(db: Session, shift: Shift) -> Shift`:
        *   Recalculates `shift.total_tickets_sold_instant` and `shift.total_value_instant` by summing `count` and `price` from all `SalesEntry` records associated with this `shift`.
        *   Recalculates `shift.net_drop_value` using the formula: `shift.calculated_delta_online_sales + shift.total_value_instant - (shift.calculated_delta_online_payouts + shift.calculated_delta_instant_payouts)`.
        *   Returns the updated shift object.

2.  **Modify `app/data/crud_sales_entries.py`:**
    *   `create_sales_entry(db: Session, sales_entry_data: SalesEntry) -> SalesEntry`:
        *   The `sales_entry_data` object passed in will now have `shift_id` set. Ensure this is handled.

**III. Service Layer Changes:**

1.  **New `app/services/shift_service.py`:**
    *   **`ShiftService` Class:**
        *   `create_new_shift_submission(self, db: Session, user_id: int, reported_online_sales: int, reported_online_payouts: int, reported_instant_payouts: int, sales_item_details: List[Dict[str, Any]]) -> Shift`:
            *   **Transaction Management:** This entire method should operate within a single database transaction (managed by `get_db_session` in the calling view).
            *   Create the `Shift` object using `crud_shifts.create_shift_submission`. Use `datetime.datetime.now()` for `submission_dt`.
            *   Add the new `shift_obj` to the session (`db.add(shift_obj)`).
            *   **Flush** the session (`db.flush()`) to get the `shift_obj.id` generated by the database.
            *   **Process Sales Entries:** Use the `SalesEntryService.process_and_save_sales_batch_for_shift` (method to be created/modified in `SalesEntryService`) to create `SalesEntry` records, associating them with `shift_obj.id`.
            *   **Update Aggregates:** After sales entries are processed (and conceptually added to the session), call `crud_shifts.update_shift_instant_aggregates_and_drop(db, shift_obj)`.
            *   The final commit will be handled by the `get_db_session` context manager in the view.
            *   Return the fully populated and calculated `shift_obj`.
        *   `get_shifts_for_report(self, db: Session, start_date: datetime, end_date: datetime, user_id: Optional[int] = None) -> List[Shift]`:
            *   Uses `crud_shifts.get_shifts_by_user_and_date_range`.

2.  **Modify `app/services/sales_entry_service.py`:**
    *   `create_sales_entry_for_full_book(self, db: Session, book: Book, shift_id: int) -> SalesEntry`: (Signature changes `user_id` to `shift_id`).
        *   The `SalesEntry` object should be initialized with `shift_id`.
    *   Rename/Refactor `process_and_save_sales_batch` to `process_and_save_sales_batch_for_shift(self, db: Session, shift_id: int, sales_item_details: List[Dict[str, Any]]) -> Tuple[int, int, List[str]]`:
        *   This method will be called by `ShiftService.create_new_shift_submission`.
        *   Its primary responsibility is now to create the `SalesEntry` records and link them to the provided `shift_id`.
        *   It should **not** try to update shift aggregates itself; that will be handled by the `ShiftService` after this method returns.
        *   Return counts and errors as before.

3.  **Modify `app/services/report_service.py`:**
    *   In `get_sales_report_data`, the query to fetch `SalesEntry` will need to join through `Shift` to get `User.username`.
        *   `SalesEntry -> Shift -> User`.
    *   Add `get_shifts_summary_data_for_report(self, db: Session, start_date: datetime, end_date: datetime, user_id: Optional[int] = None) -> List[Dict[str, Any]]`:
        *   Calls `ShiftService.get_shifts_for_report`.
        *   Formats data for the report table (User name, submission time, delta sales, delta payouts, instant sales, net drop).

**IV. UI Layer Changes:**

1.  **`app/ui/views/admin/sales_entry_view.py` (`SalesEntryView`):**
    *   **State Management & UI Elements:**
        *   Remove UI elements and logic related to starting/ending an "active shift" (`shift_status_label`, `start_shift_button`, `end_shift_button`). The concept of an "open shift" UI state is gone.
        *   The view will always be ready for a new submission.
    *   **Input Fields for Cumulative Daily Totals:**
        *   Add `ft.TextField` (or `NumberDecimalField`) for:
            *   `self.reported_online_sales_field`
            *   `self.reported_online_payouts_field`
            *   `self.reported_instant_payouts_field`
        *   These fields should be placed prominently, perhaps near the "Submit Shift Sales" button.
    *   **"Scan" and "Add Item" Logic (`_process_scan_and_update_table`):**
        *   This logic remains largely the same for populating the `SalesEntryItemsTable` with *instant* game sales.
        *   The `SalesEntryItemsTable` itself will manage a list of `SalesEntryItemData` objects representing tickets sold for instant games *for the current submission*.
    *   **"Submit Shift Sales" Button (rename from "Submit All Sales"):**
        *   When clicked (`_handle_submit_shift_sales_click`):
            1.  Perform client-side validation for the new cumulative total fields (must be numbers, non-negative).
            2.  Get `sales_item_details` from `self.sales_items_table_component.get_all_items_for_submission()`.
            3.  Call a new method `_open_confirm_shift_submission_dialog` which takes the entered cumulative values and the `sales_item_details`.
    *   **`_open_confirm_shift_submission_dialog(self, reported_online_sales, reported_online_payouts, reported_instant_payouts, sales_item_details)`:**
        *   **Display for Confirmation:**
            *   Show the user-entered cumulative totals.
            *   Show a summary of instant sales from `sales_item_details` (total instant tickets, total instant value).
            *   **Crucially, do NOT try to calculate and display the deltas or final drop in this dialog, as that requires DB lookups of previous shifts.** The confirmation is about what the user *entered* and the *instant sales* they are submitting.
            *   Message: "You are about to submit these sales. This will finalize this set of entries. Are you sure?"
        *   **On Confirm:** Call `_execute_database_submission` with the confirmed values.
    *   **`_execute_database_submission(self, reported_online_sales, reported_online_payouts, reported_instant_payouts, sales_item_details)`:**
        *   Call `ShiftService.create_new_shift_submission(...)` with `self.current_user.id` and the provided financial figures and sales item details.
        *   On success:
            *   Show a success message including the calculated Net Drop for the submitted shift (e.g., "Shift submitted. Net Drop: $XYZ.XX").
            *   Clear the `SalesEntryItemsTable` (`self.sales_items_table_component.load_initial_active_books()` which should now clear and load nothing, or a new method to clear it).
            *   Clear the cumulative total input fields.
            *   Optionally navigate away or refresh the view.
        *   On failure: Show an error message.
    *   **The `_prompt_for_empty_field_books_confirmation` and related logic for marking books as "all sold" can still be relevant for the *instant* sales part of the submission.**

2.  **`app/ui/views/admin_dashboard_view.py` (`AdminDashboardView`):**
    *   **`_process_full_book_sale_batch` callback:**
        *   This administrative action still needs to create `SalesEntry` records.
        *   Since it's an admin action outside a regular user's sales submission flow, it should create a *dedicated, minimal Shift record* for these entries.
        *   In `_process_full_book_sale_batch`, before the loop:
            1.  Use `datetime.datetime.now()` for the submission time.
            2.  For `reported_total_online_sales_today`, `reported_total_online_payouts_today`, `reported_total_instant_payouts_today`: these should be set to **0** (or fetched if there's a way to know the true daily totals at this admin action time, but 0 is safer to avoid skewing delta calculations for regular user submissions). The deltas for these will then also be 0.
            3.  Call `crud_shifts.create_shift_submission` to get the `shift_obj` and its `id`. This shift is specifically for these admin-triggered full book sales.
            4.  Pass this `shift_id` to `self.sales_entry_service.create_sales_entry_for_full_book`.
            5.  After the loop, call `crud_shifts.update_shift_instant_aggregates_and_drop(db, shift_obj)` to finalize this specific admin shift's `total_value_instant` and `net_drop_value`. The net drop for such a shift will likely just be `total_value_instant` if other financial figures are 0.

3.  **`app/ui/views/admin/reports/sales_by_date_report_view.py` (`SalesByDateReportView`):**
    *   **Data Fetching (`_generate_report_data_and_display`):**
        *   The existing `self.report_service.get_sales_report_data` fetches `SalesEntry` details.
        *   Fetch shift summary data: `shifts_summary_data = self.report_service.get_shifts_summary_data_for_report(...)` using the same filters.
    *   **UI Table for Shifts:**
        *   Add/Update the `PaginatedDataTable` instance (`self.shifts_summary_table`) to display shift submission summaries.
        *   **Columns:** `Submission Time`, `User`, `Delta Online Sales ($)`, `Delta Online Payouts ($)`, `Delta Instant Payouts ($)`, `Instant Sales Tickets`, `Instant Sales Value ($)`, `Net Drop ($)`.
        *   Populate this table with `shifts_summary_data`.
    *   **Layout:** Add this new table below the existing sales entries table.
    *   **Summary Totals:** Include aggregated totals for the shift summary table (e.g., sum of all net drops, sum of delta online sales).

4.  **`app/utils/pdf_generator.py` (`PDFGenerator`):**
    *   Add/Update a method: `generate_shifts_summary_table(self, data: List[Dict[str, Any]], column_headers: List[str], column_widths: Optional[List[float]] = None)`:
        *   Tailored for the shift submission summary columns.
        *   Include grand totals for relevant columns.
    *   Modify `generate_sales_report_pdf_from_data`:
        *   Accept `shifts_summary_data: List[Dict[str, Any]]`.
        *   After the sales entries table, call `self.generate_shifts_summary_table(shifts_summary_data, ...)`.

**V. Database Initialization (`app/data/database.py`):**

*   Ensure `Shift` model is part of `Base.metadata.create_all(bind=engine)`.

**VI. Key Calculation Logic Points (Re-emphasize):**

*   **Delta Calculation in `crud_shifts.create_shift_submission`:** This is critical. For each `Shift` being created, its `calculated_delta_...` fields depend on the sum of *previous* `calculated_delta_...` fields from *other shifts on the same calendar_date*. This ensures that if User A reports $100 online sales, then User B reports $150, User B's delta is $50. If User C then reports $120 (perhaps an error or a correction from the terminal), User C's delta would be $120 - ($100 + $50) = -$30.
*   **Net Drop Calculation in `crud_shifts.update_shift_instant_aggregates_and_drop`:** Uses the *calculated deltas* for that specific shift, not the reported cumulative totals.

**VII. Testing Focus:**
*   Delta calculations for online sales, online payouts, and instant payouts across multiple submissions on the same day by different users.
*   Correct aggregation of instant sales (`total_tickets_sold_instant`, `total_value_instant`) within each shift.
*   Accurate `net_drop_value` calculation for each shift.
*   Sales entries correctly linked to their parent shift submission.
*   Reports correctly show sales entries linked to users (via shifts) and the detailed shift submission table with deltas and net drops.
*   PDF reports include both sections accurately.
*   "Full Book Sale" by admin creates an appropriate, isolated shift record.