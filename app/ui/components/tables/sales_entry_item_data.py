import flet as ft
from typing import Optional, Callable, Union, Dict # Added Dict
from app.core.models import Book as BookModel
from app.constants import REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER

class SalesEntryItemData:
    def __init__(self,
                 book_model: BookModel,
                 on_change_callback: Callable[['SalesEntryItemData'], None]):

        self.book_model = book_model
        self.on_change_callback = on_change_callback

        self.book_db_id: int = book_model.id
        self.game_db_id: int = book_model.game_id
        self.game_name: str = book_model.game.name if book_model.game else "N/A"
        self.book_number: str = book_model.book_number
        self.game_price: int = book_model.game.price if book_model.game else 0
        self.db_current_ticket_no: int = book_model.current_ticket_number
        self.game_total_tickets: int = book_model.game.total_tickets if book_model.game else 0
        self.ticket_order: str = book_model.ticket_order

        self.ui_new_ticket_no_str: str = ""
        self.ui_new_ticket_no_ref: Optional[ft.TextField] = None
        self._textfield_error_message: Optional[str] = None

        self.tickets_sold_calculated: int = 0
        self.amount_calculated: int = 0
        self.is_processed_for_sale: bool = False
        self.all_tickets_sold_confirmed: bool = False

        self.row_highlight_color: Optional[str] = None
        self.unique_id: str = f"book-{self.book_db_id}"

    def _calculate_sales(self) -> bool: # Return bool if meaningful change
        prev_tickets_sold = self.tickets_sold_calculated
        prev_amount = self.amount_calculated
        prev_is_processed = self.is_processed_for_sale
        prev_highlight = self.row_highlight_color
        prev_textfield_error = self._textfield_error_message

        self.tickets_sold_calculated = 0
        self.amount_calculated = 0
        self.is_processed_for_sale = False
        self.row_highlight_color = None
        self._textfield_error_message = None

        book_state_before_this_entry = self.db_current_ticket_no
        new_book_state_after_this_entry = -999 # Sentinel for "not validly determined"

        valid_input_for_calc = False

        if self.all_tickets_sold_confirmed:
            if self.ticket_order == REVERSE_TICKET_ORDER:
                new_book_state_after_this_entry = -1 # State after selling ticket 0 (0-indexed from N-1 down to 0)
            else: # FORWARD_TICKET_ORDER
                new_book_state_after_this_entry = self.game_total_tickets # State after selling ticket N-1
            self.is_processed_for_sale = True
            valid_input_for_calc = True
        elif not self.ui_new_ticket_no_str: # Empty string - valid, means no tickets entered for this item yet
            self.is_processed_for_sale = False # Not processed for sale unless all_sold_confirmed
            valid_input_for_calc = True # But valid for calculation (results in 0 sales)
            new_book_state_after_this_entry = book_state_before_this_entry # No change in state
        elif self.ui_new_ticket_no_str == "-" or \
                (self.ui_new_ticket_no_str.startswith('-') and not self.ui_new_ticket_no_str[1:].isdigit()) or \
                (not self.ui_new_ticket_no_str.startswith('-') and not self.ui_new_ticket_no_str.isdigit()):
            # Contains non-digits other than a valid leading minus
            self.row_highlight_color = ft.Colors.RED_100
            self._textfield_error_message = "Invalid number"
        else: # Potentially valid number (digits or -digit)
            try:
                entered_num = int(self.ui_new_ticket_no_str)
                is_valid_range = False
                if self.ticket_order == REVERSE_TICKET_ORDER:
                    is_valid_range = (-1 <= entered_num <= book_state_before_this_entry) and (entered_num <= self.game_total_tickets -1) # Allow -1 only for reverse
                else: # FORWARD
                    is_valid_range = (book_state_before_this_entry <= entered_num <= self.game_total_tickets)

                if not is_valid_range:
                    self.row_highlight_color = ft.Colors.RED_100
                    hint_range = f"-1 to {book_state_before_this_entry}" if self.ticket_order == REVERSE_TICKET_ORDER else f"{book_state_before_this_entry} to {self.game_total_tickets}"
                    self._textfield_error_message = f"Invalid: {hint_range}"
                else:
                    new_book_state_after_this_entry = entered_num
                    self.is_processed_for_sale = True
                    valid_input_for_calc = True
            except ValueError: # Should be caught by earlier checks but safeguard
                self.row_highlight_color = ft.Colors.RED_100
                self._textfield_error_message = "Not a number"

        if valid_input_for_calc and self.is_processed_for_sale: # Only if a valid end state is determined for processing
            if self.ticket_order == REVERSE_TICKET_ORDER:
                self.tickets_sold_calculated = book_state_before_this_entry - new_book_state_after_this_entry
            else: # FORWARD_TICKET_ORDER
                self.tickets_sold_calculated = new_book_state_after_this_entry - book_state_before_this_entry

            if self.tickets_sold_calculated < 0: # Should be caught by range checks
                self.tickets_sold_calculated = 0; self.is_processed_for_sale = False; self.row_highlight_color = ft.Colors.YELLOW_100

            self.amount_calculated = self.tickets_sold_calculated * self.game_price
            if self.is_processed_for_sale:
                self.row_highlight_color = ft.Colors.GREEN_ACCENT_100 if not self.all_tickets_sold_confirmed else ft.Colors.CYAN_100
        elif not self.ui_new_ticket_no_str: # Empty string, valid but 0 sales
            self.tickets_sold_calculated = 0
            self.amount_calculated = 0
            self.is_processed_for_sale = False # Not processed for submission unless confirmed_all_sold
            self.row_highlight_color = None # No highlight for empty, not-yet-processed

        meaningful_change = (
                prev_tickets_sold != self.tickets_sold_calculated or
                prev_amount != self.amount_calculated or
                prev_is_processed != self.is_processed_for_sale or
                prev_highlight != self.row_highlight_color or
                prev_textfield_error != self._textfield_error_message
        )
        return meaningful_change

    def update_scanned_ticket_number(self, new_ticket_str: str):
        self.ui_new_ticket_no_str = new_ticket_str
        self.all_tickets_sold_confirmed = False
        self._textfield_error_message = None # Clear previous error from manual entry

        if self.ui_new_ticket_no_ref:
            self.ui_new_ticket_no_ref.value = self.ui_new_ticket_no_str
            self.ui_new_ticket_no_ref.error_text = None
            if self.ui_new_ticket_no_ref.page: self.ui_new_ticket_no_ref.update()

        if self._calculate_sales():
            self.on_change_callback(self)

    def confirm_all_sold(self):
        self.all_tickets_sold_confirmed = True
        if self.ticket_order == REVERSE_TICKET_ORDER:
            self.ui_new_ticket_no_str = "-1"
        else:
            self.ui_new_ticket_no_str = str(self.game_total_tickets)
        self._textfield_error_message = None

        if self.ui_new_ticket_no_ref:
            self.ui_new_ticket_no_ref.value = self.ui_new_ticket_no_str
            self.ui_new_ticket_no_ref.error_text = None
            if self.ui_new_ticket_no_ref.page: self.ui_new_ticket_no_ref.update()

        if self._calculate_sales():
            self.on_change_callback(self)

    def _handle_textfield_change(self, e: ft.ControlEvent):
        current_tf_value = e.control.value.strip()
        if current_tf_value == self.ui_new_ticket_no_str and e.control.error_text == self._textfield_error_message:
            return

        self.ui_new_ticket_no_str = current_tf_value
        if self.all_tickets_sold_confirmed: # User typing overrides programmatic 'all_sold'
            is_all_sold_value_still_typed = \
                (self.ticket_order == REVERSE_TICKET_ORDER and self.ui_new_ticket_no_str == "-1") or \
                (self.ticket_order == FORWARD_TICKET_ORDER and self.ui_new_ticket_no_str == str(self.game_total_tickets))
            if not is_all_sold_value_still_typed:
                self.all_tickets_sold_confirmed = False

        meaningful_change = self._calculate_sales()

        if self.ui_new_ticket_no_ref:
            if self.ui_new_ticket_no_ref.error_text != self._textfield_error_message:
                self.ui_new_ticket_no_ref.error_text = self._textfield_error_message
                meaningful_change = True # Error status change is meaningful
            # Update the textfield control itself only if its value differs from our internal state.
            # This helps break loops if the update itself triggers on_change.
            if self.ui_new_ticket_no_ref.value != self.ui_new_ticket_no_str:
                self.ui_new_ticket_no_ref.value = self.ui_new_ticket_no_str
                meaningful_change = True
            if self.ui_new_ticket_no_ref.page:
                self.ui_new_ticket_no_ref.update()

        if meaningful_change:
            self.on_change_callback(self)

    def get_data_for_submission(self) -> Dict[str, Union[int, str, bool]]:
        return {
            "book_db_id": self.book_db_id,
            "db_current_ticket_no": self.db_current_ticket_no,
            "ui_new_ticket_no_str": self.ui_new_ticket_no_str,
            "tickets_sold_calculated": self.tickets_sold_calculated,
            "amount_calculated": self.amount_calculated,
            "all_tickets_sold_confirmed": self.all_tickets_sold_confirmed,
        }

    def to_datarow(self) -> ft.DataRow:
        if self.ui_new_ticket_no_ref is None:
            self.ui_new_ticket_no_ref = ft.TextField(
                hint_text="Tkt #", value=self.ui_new_ticket_no_str,
                on_submit=self._handle_textfield_change,
                on_blur=self._handle_textfield_change,
                text_align=ft.TextAlign.RIGHT, height=45,
                content_padding=ft.padding.symmetric(horizontal=6, vertical=4),
                border_radius=6, text_size=13,
                input_filter=ft.InputFilter(r"^-?[0-9]*$"), # Allow empty, numbers, and -1
                error_text=self._textfield_error_message
            )
        else:
            # Explicitly set value and error_text from internal state.
            # This ensures the TextField reflects the SalesEntryItemData's truth.
            self.ui_new_ticket_no_ref.value = self.ui_new_ticket_no_str
            self.ui_new_ticket_no_ref.error_text = self._textfield_error_message

        price_display = f"${self.game_price}"
        amount_display = f"${self.amount_calculated}"

        return ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(f"{self.game_name} (G:{self.book_model.game.game_number}) - Bk.{self.book_number}", weight=ft.FontWeight.W_500, size=13)),
                ft.DataCell(ft.Text(price_display, text_align=ft.TextAlign.RIGHT, size=13)),
                ft.DataCell(ft.Text(str(self.db_current_ticket_no), text_align=ft.TextAlign.RIGHT, size=13)),
                ft.DataCell(ft.Container(content=self.ui_new_ticket_no_ref, width=90, alignment=ft.alignment.center_right)),
                ft.DataCell(ft.Text(str(self.tickets_sold_calculated), text_align=ft.TextAlign.RIGHT, weight=ft.FontWeight.BOLD, size=13)),
                ft.DataCell(ft.Text(amount_display, text_align=ft.TextAlign.RIGHT, weight=ft.FontWeight.BOLD, size=13)),
            ],
            color=self.row_highlight_color
        )