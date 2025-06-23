import logging
import flet as ft
from typing import Callable, Dict, Optional, Tuple, List

logger = logging.getLogger("lottery_manager_app")

class ScanInputHandler:
    """
    Handles scan input by queueing valid scans and processing them sequentially
    on the Flet UI thread. This approach is robust against rapid-fire scans even
    on slow machines, preventing lost inputs and logical race conditions.
    """
    def __init__(
            self,
            scan_text_field: ft.TextField,
            on_scan_complete: Callable[[Dict[str, str]], None],
            on_scan_error: Callable[[str], None],
            require_ticket: bool = False,
            auto_clear_on_complete: bool = True,
            auto_focus_on_complete: bool = True,
    ):
        self.scan_text_field = scan_text_field
        self.on_scan_complete = on_scan_complete
        self.on_scan_error = on_scan_error
        self.require_ticket = require_ticket
        self.auto_clear_on_complete = auto_clear_on_complete
        self.auto_focus_on_complete = auto_focus_on_complete

        self._scan_queue: List[Dict[str, str]] = []
        self._is_processing = False

        from app.constants import GAME_LENGTH, BOOK_LENGTH, TICKET_LENGTH
        self.GAME_LENGTH = GAME_LENGTH
        self.BOOK_LENGTH = BOOK_LENGTH
        self.TICKET_LENGTH = TICKET_LENGTH

        if self.require_ticket:
            self.expected_length = self.GAME_LENGTH + self.BOOK_LENGTH + self.TICKET_LENGTH
        else:
            self.expected_length = self.GAME_LENGTH + self.BOOK_LENGTH

        self.scan_text_field.on_submit = self._handle_input_producer
        self.scan_text_field.on_change = self._handle_input_producer

    def _parse_scan_data(self, scan_value: str) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
        if len(scan_value) < self.expected_length:
            return None, None

        game_no_str = scan_value[:self.GAME_LENGTH]
        book_no_str = scan_value[self.GAME_LENGTH : self.GAME_LENGTH + self.BOOK_LENGTH]
        parsed_data = {}

        if not (game_no_str.isdigit() and len(game_no_str) == self.GAME_LENGTH):
            return None, f"Invalid Game No. format: '{game_no_str}'."
        parsed_data['game_no'] = game_no_str

        if not (book_no_str.isdigit() and len(book_no_str) == self.BOOK_LENGTH):
            return None, f"Invalid Book No. format: '{book_no_str}'."
        parsed_data['book_no'] = book_no_str

        if self.require_ticket:
            ticket_part_start = self.GAME_LENGTH + self.BOOK_LENGTH
            ticket_no_str = scan_value[ticket_part_start : ticket_part_start + self.TICKET_LENGTH]
            if not (ticket_no_str.isdigit() and len(ticket_no_str) == self.TICKET_LENGTH):
                return None, f"Invalid Ticket No. format: '{ticket_no_str}'."
            parsed_data['ticket_no'] = ticket_no_str

        return parsed_data, None

    def _handle_input_producer(self, e: ft.ControlEvent):
        """Producer: Validates, queues the input, and kicks off the consumer loop if idle."""
        scan_value = e.control.value.strip()

        if len(scan_value) < self.expected_length:
            return

        if self.auto_clear_on_complete:
            e.control.value = ""
            e.control.update()

        parsed_data, error_msg = self._parse_scan_data(scan_value)

        if error_msg:
            self.on_scan_error(error_msg)
            return

        if parsed_data:
            self._scan_queue.append(parsed_data)

            # Atomically check and start the processing loop.
            if not self._is_processing:
                self._is_processing = True
                self._process_queue_motor()

    def _process_queue_motor(self):
        """
        Consumer Motor: This is the core of the safe processing loop.
        It processes one item, and upon completion, it checks for more work.
        This structure prevents recursive calls and ensures atomicity.
        """
        if not self._scan_queue:
            # Queue is empty, we can safely release the lock and stop.
            self._is_processing = False

            # Manage focus at the very end of a processing batch
            if self.auto_focus_on_complete and self.scan_text_field.page:
                self.scan_text_field.focus()
            return

        # Get the next item BUT KEEP THE LOCK
        scan_data_to_process = self._scan_queue.pop(0)

        try:
            # Call the potentially slow callback to do the main work
            self.on_scan_complete(scan_data_to_process)
        except Exception as e:
            logger.error(f"ScanInputHandler: Unexpected error in consumer callback: {e}", exc_info=True)
            self.on_scan_error("A critical error occurred while processing a queued scan.")
        finally:
            # --- CRITICAL SECTION ---
            # The work for the current item is done.
            # We immediately call ourself to check for the next item BEFORE releasing the lock.
            # This ensures that no producer can start a competing loop.
            self._process_queue_motor()

    def clear_input(self):
        self.scan_text_field.value = ""
        if self.scan_text_field.page:
            self.scan_text_field.update()

    def clear_queue(self):
        self._scan_queue.clear()

    def focus_input(self):
        if self.scan_text_field.page:
            self.scan_text_field.focus()