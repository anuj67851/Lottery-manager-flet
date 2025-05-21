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
            debounce_ms: int = 200,
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
        self._processing_lock = threading.Lock()

        self.scan_text_field.on_change = self._handle_input_change
        self.scan_text_field.on_submit = self._handle_input_submit

    def _parse_scan_data(self, scan_value: str) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
        if len(scan_value) < self.expected_length:
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
            if len(scan_value) < (GAME_LENGTH + BOOK_LENGTH + TICKET_LENGTH):
                return None, f"Scan input too short for ticket part. Expected {TICKET_LENGTH} more chars."
            ticket_no_str = scan_value[GAME_LENGTH + BOOK_LENGTH : GAME_LENGTH + BOOK_LENGTH + TICKET_LENGTH]
            if not (ticket_no_str.isdigit() and len(ticket_no_str) == TICKET_LENGTH):
                return None, f"Invalid Ticket No. format: '{ticket_no_str}'. Expected {TICKET_LENGTH} digits."
            parsed_data['ticket_no'] = ticket_no_str
        return parsed_data, None

    def _execute_processing(self):
        if not self._processing_lock.acquire(blocking=False):
            return

        value_snapshot = "" # Initialize
        try:
            value_snapshot = self.scan_text_field.value.strip() if self.scan_text_field.value else ""

            if len(value_snapshot) < self.expected_length:
                self.on_scan_error(f"Scan input too short. Expected {self.expected_length} chars, got {len(value_snapshot)}.")
                # Do not return yet, allow finally block to clear/focus if needed
                # The rest of the processing will be skipped due to length check.
            else: # Only proceed with parsing if length is initially okay
                input_to_parse = value_snapshot[:self.expected_length]
                parsed_data, error_msg = self._parse_scan_data(input_to_parse)

                if error_msg:
                    self.on_scan_error(error_msg)
                elif parsed_data:
                    self.on_scan_complete(parsed_data)
                # If neither error_msg nor parsed_data, it's an unexpected state from _parse_scan_data
                # (though current _parse_scan_data always returns one or the other if input length is fine).
                # This case is implicitly handled by the outer except Exception if something truly odd happens.

        except Exception as e:
            # Catch any other unexpected error during the processing
            print(f"ScanInputHandler: Unexpected error in _execute_processing: {e}") # Log for debugging
            self.on_scan_error("An unexpected error occurred during scan processing. Please try again.")
        finally:
            # Ensure field is cleared and focused regardless of how the try block exited,
            # but only if auto-options are enabled.
            # This part needs to run after on_scan_complete or on_scan_error has potentially updated UI.
            if self.auto_clear_on_complete:
                self.scan_text_field.value = ""
                if self.scan_text_field.page:
                    self.scan_text_field.update()

            if self.auto_focus_on_complete and self.scan_text_field.page:
                self.scan_text_field.focus()

            self._processing_lock.release()


    def _handle_input_change(self, e: ft.ControlEvent):
        if self._debounce_timer:
            self._debounce_timer.cancel()
        self._debounce_timer = threading.Timer(
            self.debounce_time_seconds,
            self._execute_processing
        )
        self._debounce_timer.start()

    def _handle_input_submit(self, e: ft.ControlEvent):
        if self._debounce_timer:
            self._debounce_timer.cancel()
        self._execute_processing()

    def clear_input(self):
        if self._debounce_timer:
            self._debounce_timer.cancel()
        # No lock needed here if it's just setting value,
        # but if it could interfere with _execute_processing, lock might be considered.
        # For simplicity, direct update.
        self.scan_text_field.value = ""
        if self.scan_text_field.page:
            self.scan_text_field.update()

    def focus_input(self):
        if self.scan_text_field.page:
            self.scan_text_field.focus()