import flet as ft
from typing import Callable, Dict, Optional, Tuple
import threading

from app.constants import GAME_LENGTH, BOOK_LENGTH, TICKET_LENGTH, MIN_REQUIRED_SCAN_LENGTH_WITH_TICKET, MIN_REQUIRED_SCAN_LENGTH

class ScanInputHandler:
    def __init__(
            self,
            scan_text_field: ft.TextField,
            on_scan_complete: Callable[[Dict[str, str]], None],
            on_scan_error: Callable[[str], None],
            require_ticket: bool = False,
            auto_clear_on_complete: bool = True,
            auto_focus_on_complete: bool = True,
            debounce_ms: int = 200, # Debounce time in milliseconds (tune this value)
    ):
        self.scan_text_field = scan_text_field
        self.on_scan_complete = on_scan_complete
        self.on_scan_error = on_scan_error
        self.require_ticket = require_ticket
        self.auto_clear_on_complete = auto_clear_on_complete
        self.auto_focus_on_complete = auto_focus_on_complete
        self.debounce_time_seconds = debounce_ms / 1000.0

        self.expected_length = MIN_REQUIRED_SCAN_LENGTH_WITH_TICKET if require_ticket else MIN_REQUIRED_SCAN_LENGTH
        self._debounce_timer: Optional[threading.Timer] = None
        # Using a lock ensures that the _execute_processing logic is atomic for a given handler instance
        self._processing_lock = threading.Lock()

        self.scan_text_field.on_change = self._handle_input_change
        self.scan_text_field.on_submit = self._handle_input_submit # Keep for manual enter/scanner suffix

    def _parse_scan_data(self, scan_value: str) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
        # This function assumes 'scan_value' is the exact segment (already truncated) to be parsed.
        # The length check here is for the format of this specific segment.

        if len(scan_value) < self.expected_length:
            # This error message should match your screenshot if a short string makes it here
            return None, f"Scan input too short. Expected {self.expected_length} chars, got {len(scan_value)}."

        game_no_str = scan_value[:GAME_LENGTH]
        book_no_str = scan_value[GAME_LENGTH : GAME_LENGTH + BOOK_LENGTH]
        parsed_data = {}

        if not (game_no_str.isdigit() and len(game_no_str) == GAME_LENGTH):
            return None, f"Invalid Game No. format: '{game_no_str}'. Expected {GAME_LENGTH} digits."
        parsed_data['game_no'] = game_no_str

        if not (book_no_str.isdigit() and len(book_no_str) == BOOK_LENGTH):
            return None, f"Invalid Book No. format: '{book_no_str}'. Expected {BOOK_LENGTH} digits."
        parsed_data['book_no'] = book_no_str

        if self.require_ticket:
            # Ensure the segment itself contains enough chars for the ticket part
            if len(scan_value) < (GAME_LENGTH + BOOK_LENGTH + TICKET_LENGTH):
                return None, f"Scan input too short for ticket part. Expected {TICKET_LENGTH} more chars in segment."
            ticket_no_str = scan_value[GAME_LENGTH + BOOK_LENGTH : GAME_LENGTH + BOOK_LENGTH + TICKET_LENGTH]
            if not (ticket_no_str.isdigit() and len(ticket_no_str) == TICKET_LENGTH):
                return None, f"Invalid Ticket No. format: '{ticket_no_str}'. Expected {TICKET_LENGTH} digits."
            parsed_data['ticket_no'] = ticket_no_str
        return parsed_data, None

    def _execute_processing(self):
        """
        Core processing logic. Called after debouncing or by on_submit.
        This function now reads the field's current value when it executes.
        """
        # Attempt to acquire the lock. If not available, another thread is processing.
        if not self._processing_lock.acquire(blocking=False):
            # print("ScanInputHandler: Processing already in progress. Skipping.")
            return

        try:
            # 1. Get the definitive value from the field at the moment of execution
            value_snapshot = self.scan_text_field.value.strip() if self.scan_text_field.value else ""

            # 2. Check length *before* truncation for the "too short" error message accuracy
            if len(value_snapshot) < self.expected_length:
                self.on_scan_error(f"Scan input too short. Expected {self.expected_length} chars, got {len(value_snapshot)}.")
                # Even if it's too short, we might want to clear based on settings
                if self.auto_clear_on_complete:
                    self.scan_text_field.value = ""
                if self.scan_text_field.page: self.scan_text_field.update()
                if self.auto_focus_on_complete and self.scan_text_field.page: self.scan_text_field.focus()
                return # Stop processing

            # 3. Truncate to the exact expected length for parsing (handles over-scan)
            input_to_parse = value_snapshot[:self.expected_length]

            # 4. Clear the TextField *before* any further processing or callbacks if auto_clear is on
            # This is critical to prevent leftover characters or re-processing the same scan.
            if self.auto_clear_on_complete:
                self.scan_text_field.value = ""
                if self.scan_text_field.page: # Update UI to reflect clearance
                    self.scan_text_field.update()

            # 5. Parse and call callbacks
            parsed_data, error_msg = self._parse_scan_data(input_to_parse)

            if error_msg:
                self.on_scan_error(error_msg)
            elif parsed_data:
                self.on_scan_complete(parsed_data) # Call with successfully parsed data

            # 6. Re-focus (auto_clear_on_complete has already handled field clearing if needed)
            if self.auto_focus_on_complete and self.scan_text_field.page:
                self.scan_text_field.focus()

        finally:
            self._processing_lock.release()


    def _handle_input_change(self, e: ft.ControlEvent):
        # Always cancel any existing timer when new input comes
        if self._debounce_timer:
            self._debounce_timer.cancel()

        # Schedule the _execute_processing method.
        # We don't pass the event's value directly to the timer's target function.
        # Instead, _execute_processing will read the TextField's value when it runs.
        # This ensures we process the "settled" value after the debounce period.
        self._debounce_timer = threading.Timer(
            self.debounce_time_seconds,
            self._execute_processing
        )
        self._debounce_timer.start()


    def _handle_input_submit(self, e: ft.ControlEvent): # For manual Enter press or scanner suffix
        # If on_submit is triggered (e.g. scanner sends newline/tab),
        # we want to process immediately, cancelling any pending debounce.
        if self._debounce_timer:
            self._debounce_timer.cancel()

        self._execute_processing() # Process the current content of the field


    def clear_input(self):
        """Public method to clear input, e.g., from the parent view."""
        if self._debounce_timer: # Cancel timer if clearing externally
            self._debounce_timer.cancel()
        with self._processing_lock: # Ensure consistency
            self.scan_text_field.value = ""
            if self.scan_text_field.page:
                self.scan_text_field.update()

    def focus_input(self):
        """Public method to focus input, e.g., from the parent view."""
        if self.scan_text_field.page:
            self.scan_text_field.focus()