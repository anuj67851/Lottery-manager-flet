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
        self.game_price_cents: int = book_model.game.price if book_model.game else 0 # Game price is in CENTS
        self.db_current_ticket_no: int = book_model.current_ticket_number
        self.game_total_tickets: int = book_model.game.total_tickets if book_model.game else 0
        self.ticket_order: str = book_model.ticket_order

        self.ui_new_ticket_no_str: str = ""
        self.ui_new_ticket_no_ref: Optional[ft.TextField] = None
        self._textfield_error_message: Optional[str] = None

        self.tickets_sold_calculated: int = 0
        self.amount_calculated_cents: int = 0 # Amount is now in CENTS
        self.is_processed_for_sale: bool = False
        self.all_tickets_sold_confirmed: bool = False

        self.row_highlight_color: Optional[str] = None
        self.unique_id: str = f"book-{self.book_db_id}"

    def _calculate_sales(self) -> bool:
        prev_tickets_sold = self.tickets_sold_calculated
        prev_amount_cents = self.amount_calculated_cents
        prev_is_processed = self.is_processed_for_sale
        prev_highlight = self.row_highlight_color
        prev_textfield_error = self._textfield_error_message

        self.tickets_sold_calculated = 0
        self.amount_calculated_cents = 0
        self.is_processed_for_sale = False
        self.row_highlight_color = None
        self._textfield_error_message = None

        book_state_before_this_entry = self.db_current_ticket_no
        new_book_state_after_this_entry = -999

        valid_input_for_calc = False

        if self.all_tickets_sold_confirmed:
            if self.ticket_order == REVERSE_TICKET_ORDER: new_book_state_after_this_entry = -1
            else: new_book_state_after_this_entry = self.game_total_tickets
            self.is_processed_for_sale = True; valid_input_for_calc = True
        elif not self.ui_new_ticket_no_str:
            self.is_processed_for_sale = False; valid_input_for_calc = True
            new_book_state_after_this_entry = book_state_before_this_entry
        elif self.ui_new_ticket_no_str == "-" or \
                (self.ui_new_ticket_no_str.startswith('-') and not self.ui_new_ticket_no_str[1:].isdigit()) or \
                (not self.ui_new_ticket_no_str.startswith('-') and not self.ui_new_ticket_no_str.isdigit()):
            self.row_highlight_color = ft.Colors.RED_100; self._textfield_error_message = "Invalid number"
        else:
            try:
                entered_num = int(self.ui_new_ticket_no_str)
                is_valid_range = False
                if self.ticket_order == REVERSE_TICKET_ORDER:
                    is_valid_range = (-1 <= entered_num <= book_state_before_this_entry) and (entered_num <= self.game_total_tickets -1)
                else:
                    is_valid_range = (book_state_before_this_entry <= entered_num <= self.game_total_tickets)
                if not is_valid_range:
                    self.row_highlight_color = ft.Colors.RED_100
                    hint_range = f"-1 to {book_state_before_this_entry}" if self.ticket_order == REVERSE_TICKET_ORDER else f"{book_state_before_this_entry} to {self.game_total_tickets}"
                    self._textfield_error_message = f"Invalid: {hint_range}"
                else:
                    new_book_state_after_this_entry = entered_num
                    self.is_processed_for_sale = True; valid_input_for_calc = True
            except ValueError:
                self.row_highlight_color = ft.Colors.RED_100; self._textfield_error_message = "Not a number"

        if valid_input_for_calc and self.is_processed_for_sale:
            if self.ticket_order == REVERSE_TICKET_ORDER:
                self.tickets_sold_calculated = book_state_before_this_entry - new_book_state_after_this_entry
            else:
                self.tickets_sold_calculated = new_book_state_after_this_entry - book_state_before_this_entry
            if self.tickets_sold_calculated < 0:
                self.tickets_sold_calculated = 0; self.is_processed_for_sale = False; self.row_highlight_color = ft.Colors.YELLOW_100

            # self.game_price_cents is in CENTS, so amount_calculated_cents will be in CENTS
            self.amount_calculated_cents = self.tickets_sold_calculated * self.game_price_cents
            if self.is_processed_for_sale:
                self.row_highlight_color = ft.Colors.GREEN_ACCENT_100 if not self.all_tickets_sold_confirmed else ft.Colors.CYAN_100
        elif not self.ui_new_ticket_no_str:
            self.tickets_sold_calculated = 0; self.amount_calculated_cents = 0
            self.is_processed_for_sale = False; self.row_highlight_color = None

        meaningful_change = (
                prev_tickets_sold != self.tickets_sold_calculated or
                prev_amount_cents != self.amount_calculated_cents or
                prev_is_processed != self.is_processed_for_sale or
                prev_highlight != self.row_highlight_color or
                prev_textfield_error != self._textfield_error_message
        )
        return meaningful_change

    def update_scanned_ticket_number(self, new_ticket_str: str):
        self.ui_new_ticket_no_str = new_ticket_str
        self.all_tickets_sold_confirmed = False
        self._textfield_error_message = None
        if self.ui_new_ticket_no_ref:
            self.ui_new_ticket_no_ref.value = self.ui_new_ticket_no_str
            self.ui_new_ticket_no_ref.error_text = None
            if self.ui_new_ticket_no_ref.page: self.ui_new_ticket_no_ref.update()
        if self._calculate_sales(): self.on_change_callback(self)

    def confirm_all_sold(self):
        self.all_tickets_sold_confirmed = True
        if self.ticket_order == REVERSE_TICKET_ORDER: self.ui_new_ticket_no_str = "-1"
        else: self.ui_new_ticket_no_str = str(self.game_total_tickets)
        self._textfield_error_message = None
        if self.ui_new_ticket_no_ref:
            self.ui_new_ticket_no_ref.value = self.ui_new_ticket_no_str
            self.ui_new_ticket_no_ref.error_text = None
            if self.ui_new_ticket_no_ref.page: self.ui_new_ticket_no_ref.update()
        if self._calculate_sales(): self.on_change_callback(self)

    def _handle_textfield_change(self, e: ft.ControlEvent):
        current_tf_value = e.control.value.strip()
        if current_tf_value == self.ui_new_ticket_no_str and e.control.error_text == self._textfield_error_message: return
        self.ui_new_ticket_no_str = current_tf_value
        if self.all_tickets_sold_confirmed:
            is_all_sold_value_still_typed = \
                (self.ticket_order == REVERSE_TICKET_ORDER and self.ui_new_ticket_no_str == "-1") or \
                (self.ticket_order == FORWARD_TICKET_ORDER and self.ui_new_ticket_no_str == str(self.game_total_tickets))
            if not is_all_sold_value_still_typed: self.all_tickets_sold_confirmed = False
        meaningful_change = self._calculate_sales()
        if self.ui_new_ticket_no_ref:
            if self.ui_new_ticket_no_ref.error_text != self._textfield_error_message:
                self.ui_new_ticket_no_ref.error_text = self._textfield_error_message; meaningful_change = True
            if self.ui_new_ticket_no_ref.value != self.ui_new_ticket_no_str:
                self.ui_new_ticket_no_ref.value = self.ui_new_ticket_no_str; meaningful_change = True
            if self.ui_new_ticket_no_ref.page: self.ui_new_ticket_no_ref.update()
        if meaningful_change: self.on_change_callback(self)

    def get_data_for_submission(self) -> Dict[str, Union[int, str, bool]]:
        return {
            "book_db_id": self.book_db_id,
            "db_current_ticket_no": self.db_current_ticket_no,
            "ui_new_ticket_no_str": self.ui_new_ticket_no_str,
            "tickets_sold_calculated": self.tickets_sold_calculated,
            "amount_calculated_cents": self.amount_calculated_cents, # Key name changed
            "all_tickets_sold_confirmed": self.all_tickets_sold_confirmed,
        }

    def to_datarow(self) -> ft.DataRow:
        if self.ui_new_ticket_no_ref is None:
            self.ui_new_ticket_no_ref = ft.TextField(
                hint_text="Tkt #", value=self.ui_new_ticket_no_str,
                on_submit=self._handle_textfield_change, on_blur=self._handle_textfield_change,
                text_align=ft.TextAlign.RIGHT, height=45,
                content_padding=ft.padding.symmetric(horizontal=6, vertical=4),
                border_radius=6, text_size=13,
                input_filter=ft.InputFilter(r"^-?[0-9]*$"),
                error_text=self._textfield_error_message )
        else:
            self.ui_new_ticket_no_ref.value = self.ui_new_ticket_no_str
            self.ui_new_ticket_no_ref.error_text = self._textfield_error_message

        price_display_dollars = f"${(self.game_price_cents / 100.0):.2f}" # Display in dollars
        amount_display_dollars = f"${(self.amount_calculated_cents / 100.0):.2f}" # Display in dollars

        return ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(f"{self.game_name} | Game No: {self.book_model.game.game_number} | Book No: {self.book_number}", weight=ft.FontWeight.W_500, size=13)),
                ft.DataCell(ft.Text(price_display_dollars, text_align=ft.TextAlign.RIGHT, size=13)),
                ft.DataCell(ft.Text(str(self.db_current_ticket_no), text_align=ft.TextAlign.RIGHT, size=13)),
                ft.DataCell(ft.Container(content=self.ui_new_ticket_no_ref, width=90, alignment=ft.alignment.center_right)),
                ft.DataCell(ft.Text(str(self.tickets_sold_calculated), text_align=ft.TextAlign.RIGHT, weight=ft.FontWeight.BOLD, size=13)),
                ft.DataCell(ft.Text(amount_display_dollars, text_align=ft.TextAlign.RIGHT, weight=ft.FontWeight.BOLD, size=13)),
            ],
            color=self.row_highlight_color )