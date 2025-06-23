import logging
import queue

import flet as ft
from typing import Callable, Dict, Optional, Tuple, List
import threading

from app.constants import GAME_LENGTH, BOOK_LENGTH, TICKET_LENGTH, MIN_REQUIRED_SCAN_LENGTH_WITH_TICKET, MIN_REQUIRED_SCAN_LENGTH
logger = logging.getLogger("lottery_manager_app")
class ScanInputHandler:
    """
    Handles scan input from a text field, processes the input, and calls appropriate callbacks.

    This class implements a queue-based approach to handle rapid scan inputs, ensuring that
    each scan is processed in the order it was received, without overwriting previous scans.
    When multiple scans are received in quick succession, they are added to a queue and
    processed sequentially.
    """
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
        self._scan_queue = queue.Queue()
        self._is_processing = False
        self._processing_thread = None

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

    def _process_scan_input(self, scan_value: str):
        """Process a single scan input value."""
        try:
            if len(scan_value) < self.expected_length:
                self.on_scan_error(f"Scan input too short. Expected {self.expected_length} chars, got {len(scan_value)}.")
            else:
                input_to_parse = scan_value[:self.expected_length]
                parsed_data, error_msg = self._parse_scan_data(input_to_parse)

                if error_msg:
                    self.on_scan_error(error_msg)
                elif parsed_data:
                    self.on_scan_complete(parsed_data)
        except Exception as e:
            logger.error(f"ScanInputHandler: Unexpected error in _process_scan_input: {e}", exc_info=True)
            self.on_scan_error("An unexpected error occurred during scan processing. Please try again.")
        finally:
            # Clear and focus the input field if needed
            if self.auto_clear_on_complete:
                self.scan_text_field.value = ""
                if self.scan_text_field.page:
                    self.scan_text_field.update()

            if self.auto_focus_on_complete and self.scan_text_field.page:
                self.scan_text_field.focus()

    def _process_queue(self):
        """Process all items in the scan queue."""
        with self._processing_lock:
            self._is_processing = True

        try:
            while not self._scan_queue.empty():
                scan_value = self._scan_queue.get()
                self._process_scan_input(scan_value)
                self._scan_queue.task_done()
        finally:
            with self._processing_lock:
                self._is_processing = False
                self._processing_thread = None

    def _execute_processing(self):
        """Add current input to queue and start processing if not already processing."""
        value_snapshot = self.scan_text_field.value.strip() if self.scan_text_field.value else ""

        if value_snapshot:
            # Add the current value to the queue
            self._scan_queue.put(value_snapshot)

            # Start processing thread if not already running
            with self._processing_lock:
                if not self._is_processing:
                    self._processing_thread = threading.Thread(target=self._process_queue)
                    self._processing_thread.daemon = True
                    self._processing_thread.start()


    def _handle_input_change(self, e: ft.ControlEvent):
        # Cancel any existing debounce timer
        if self._debounce_timer:
            self._debounce_timer.cancel()

        # Start a new debounce timer
        self._debounce_timer = threading.Timer(
            self.debounce_time_seconds,
            self._execute_processing
        )
        self._debounce_timer.start()

    def _handle_input_submit(self, e: ft.ControlEvent):
        # Cancel any existing debounce timer
        if self._debounce_timer:
            self._debounce_timer.cancel()

        # Process the input immediately
        self._execute_processing()

    def clear_input(self):
        # Cancel any existing debounce timer
        if self._debounce_timer:
            self._debounce_timer.cancel()

        # Clear the text field
        self.scan_text_field.value = ""
        if self.scan_text_field.page:
            self.scan_text_field.update()

        # Note: We don't clear the queue here to allow any pending scans to be processed

    def focus_input(self):
        if self.scan_text_field.page:
            self.scan_text_field.focus()

    def clear_queue(self):
        """
        Clears the scan queue, discarding any pending scan inputs.
        This can be useful in situations where you want to reset the system
        or discard pending scans.
        """
        # Use a lock to ensure thread safety
        with self._processing_lock:
            # Create a new empty queue
            self._scan_queue = queue.Queue()

            # Note: We don't stop the current processing thread,
            # as it will finish processing the current item and then exit
            # when it finds the queue empty
