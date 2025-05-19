import flet as ft
from typing import Callable, Dict, Optional, Tuple

from app.constants import GAME_LENGTH, BOOK_LENGTH, TICKET_LENGTH, MIN_REQUIRED_SCAN_LENGTH_WITH_TICKET, MIN_REQUIRED_SCAN_LENGTH


class ScanInputHandler:
    """
    Handles logic for a scan input TextField, including parsing and validation.
    This is not a Flet Control, but a helper to be used with a ft.TextField.
    """
    def __init__(
            self,
            scan_text_field: ft.TextField,
            on_scan_complete: Callable[[Dict[str, str]], None], # Callback with parsed data: {'game_no', 'book_no', 'ticket_no'?}
            on_scan_error: Callable[[str], None], # Callback with error message
            require_ticket: bool = False, # If true, expects game+book+ticket
            auto_clear_on_complete: bool = True,
            auto_focus_on_complete: bool = True,
    ):
        self.scan_text_field = scan_text_field
        self.on_scan_complete = on_scan_complete
        self.on_scan_error = on_scan_error
        self.require_ticket = require_ticket
        self.auto_clear_on_complete = auto_clear_on_complete
        self.auto_focus_on_complete = auto_focus_on_complete

        self.expected_length = MIN_REQUIRED_SCAN_LENGTH_WITH_TICKET if require_ticket else MIN_REQUIRED_SCAN_LENGTH

        # Attach the handler to the TextField's on_change and on_submit
        self.scan_text_field.on_change = self._handle_input_change
        self.scan_text_field.on_submit = self._handle_input_submit # For manual Enter press

    def _parse_scan_data(self, scan_value: str) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
        """
        Parses the scan value into game, book, and optionally ticket numbers.
        Returns (parsed_data_dict, error_message_or_none).
        """
        scan_value = scan_value.strip()

        if len(scan_value) < self.expected_length:
            return None, f"Scan input too short. Expected {self.expected_length} chars, got {len(scan_value)}."

        # Truncate to expected length to avoid issues with over-scans if QR has more data
        scan_value = scan_value[:self.expected_length]

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
            if len(scan_value) < GAME_LENGTH + BOOK_LENGTH + TICKET_LENGTH:
                return None, f"Scan input too short for ticket. Expected {TICKET_LENGTH} more chars."
            ticket_no_str = scan_value[GAME_LENGTH + BOOK_LENGTH : GAME_LENGTH + BOOK_LENGTH + TICKET_LENGTH]
            if not (ticket_no_str.isdigit() and len(ticket_no_str) == TICKET_LENGTH):
                return None, f"Invalid Ticket No. format: '{ticket_no_str}'. Expected {TICKET_LENGTH} digits."
            parsed_data['ticket_no'] = ticket_no_str

        return parsed_data, None


    def _process_input(self, current_value: str):
        """Core logic to process the input value from the TextField."""
        if len(current_value) >= self.expected_length:
            parsed_data, error_msg = self._parse_scan_data(current_value)

            if error_msg:
                self.on_scan_error(error_msg)
                # Optionally, clear field on error too, or let user correct
                # self.scan_text_field.value = ""
            elif parsed_data:
                self.on_scan_complete(parsed_data)

            if self.auto_clear_on_complete or error_msg : # Clear on success or if there was an error during parse attempt
                self.scan_text_field.value = ""

            if self.scan_text_field.page:
                self.scan_text_field.update()

            if self.auto_focus_on_complete and self.scan_text_field.page:
                self.scan_text_field.focus()


    def _handle_input_change(self, e: ft.ControlEvent):
        """Attached to TextField's on_change."""
        current_value = e.control.value.strip() if e.control.value else ""
        # Process only if length meets criteria, typical for scanner auto-submit behavior
        if len(current_value) >= self.expected_length:
            self._process_input(current_value)

    def _handle_input_submit(self, e: ft.ControlEvent):
        """Attached to TextField's on_submit (e.g., Enter key)."""
        current_value = e.control.value.strip() if e.control.value else ""
        # Process regardless of length if submitted, but parsing will still check length
        self._process_input(current_value)

    def clear_input(self):
        self.scan_text_field.value = ""
        if self.scan_text_field.page:
            self.scan_text_field.update()

    def focus_input(self):
        if self.scan_text_field.page:
            self.scan_text_field.focus()