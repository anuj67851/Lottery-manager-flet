import threading
import time # For delayed_focus

import flet as ft
from typing import List, Callable, Optional, Dict, Any, Tuple

from sqlalchemy.orm import Session

from app.constants import (
    GAME_LENGTH, BOOK_LENGTH, TICKET_LENGTH,
    BOOK_ACTION_ADD_NEW, BOOK_ACTION_FULL_SALE, BOOK_ACTION_ACTIVATE,
    REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER # For checking if book is sold out
)
from app.core.models import User, Game as GameModel, Book as BookModel # Added BookModel
from app.services.game_service import GameService
from app.services.book_service import BookService # Added BookService for validations
from app.data.database import get_db_session
from app.core.exceptions import ValidationError, DatabaseError, GameNotFoundError, BookNotFoundError # Added BookNotFoundError
from app.data import crud_games
from app.ui.components.widgets import NumberDecimalField
from app.ui.components.common.scan_input_handler import ScanInputHandler


class TempBookActionItem:
    """Represents a book temporarily listed in the dialog for an action."""
    def __init__(self, game_model: GameModel, book_number_str: str,
                 book_model_ref: Optional[BookModel] = None, # Optional BookModel if it exists
                 ticket_number_str: Optional[str] = None):
        self.game_id: int = game_model.id
        self.game_number_str: str = str(game_model.game_number).zfill(GAME_LENGTH)
        self.book_number_str: str = book_number_str
        self.ticket_number_str: Optional[str] = ticket_number_str

        self.game_name: str = game_model.name
        self.game_price: int = game_model.price
        self.total_tickets: int = game_model.total_tickets
        self.default_ticket_order: str = game_model.default_ticket_order
        self.is_game_expired: bool = game_model.is_expired

        self.unique_key: str = f"{self.game_number_str}-{self.book_number_str}"
        self.game_model_ref: GameModel = game_model
        self.book_model_ref: Optional[BookModel] = book_model_ref # Store if book exists

    def to_datarow(self, on_remove_callback: Callable[['TempBookActionItem'], None], action_type: str) -> ft.DataRow:
        details_parts = [
            f"Game: {self.game_name} ({self.game_number_str})",
            f"Price: ${self.game_price}",
            f"Tickets: {self.total_tickets}",
        ]
        if self.ticket_number_str: # Should not be present for these actions
            details_parts.append(f"Ticket: {self.ticket_number_str}")

        action_specific_display = ""
        if self.book_model_ref: # If book exists, show current status relevant to action
            if action_type == BOOK_ACTION_FULL_SALE:
                status = "Active" if self.book_model_ref.is_active else ("Finished" if self.book_model_ref.finish_date else "Inactive")
                action_specific_display = f"Status: {status}, Value: ${self.game_price * self.total_tickets}"
            elif action_type == BOOK_ACTION_ACTIVATE:
                status = "Active" if self.book_model_ref.is_active else ("Finished" if self.book_model_ref.finish_date else "Inactive")
                action_specific_display = f"Status: {status}, Order: {self.book_model_ref.ticket_order.capitalize()}"
        elif action_type == BOOK_ACTION_ADD_NEW: # Book doesn't exist yet
            action_specific_display = f"Order: {self.default_ticket_order.capitalize()}"


        return ft.DataRow(cells=[
            ft.DataCell(ft.Text(self.book_number_str, weight=ft.FontWeight.BOLD)),
            ft.DataCell(ft.Text(" | ".join(details_parts))),
            ft.DataCell(ft.Text(action_specific_display, size=11)),
            ft.DataCell(ft.IconButton(ft.Icons.REMOVE_CIRCLE_OUTLINE, icon_color=ft.Colors.RED_ACCENT_700,
                                      on_click=lambda e: on_remove_callback(self), tooltip="Remove from list"))
        ])

    def to_submission_dict(self) -> Dict[str, Any]:
        # For ADD_NEW, book_id won't exist yet.
        # For FULL_SALE/ACTIVATE, book_model_ref will contain the ID.
        book_id = self.book_model_ref.id if self.book_model_ref else None
        return {
            "game_id": self.game_id,
            "book_id": book_id, # ID of the existing book, if applicable
            "game_number_str": self.game_number_str,
            "book_number_str": self.book_number_str,
            "ticket_number_str": self.ticket_number_str, # Usually None for these actions
            "game_model_ref": self.game_model_ref,
            "book_model_ref": self.book_model_ref
        }


class BookActionDialog(ft.AlertDialog):
    """
    A generic dialog for performing actions on a list of books selected via scan or manual entry.
    """
    def __init__(
            self,
            page_ref: ft.Page,
            current_user_ref: User,
            dialog_title: str,
            action_button_text: str,
            action_type: str,
            on_confirm_batch_callback: Callable[[Session, List[Dict[str, Any]], User], Tuple[int, int, List[str]]],
            game_service: GameService,
            book_service: BookService, # Added BookService
            on_success_trigger_refresh: Optional[Callable[[], None]] = None,
            require_ticket_scan: bool = False,
            dialog_height_ratio: float = 0.85,
            dialog_width: int = 700, # Increased width slightly for better display
    ):
        super().__init__()

        self.page = page_ref
        self.current_user = current_user_ref
        self.dialog_title_text = dialog_title
        self.action_button_text = action_button_text
        self.action_type = action_type
        self.on_confirm_batch_callback = on_confirm_batch_callback
        self.game_service = game_service
        self.book_service = book_service # Store BookService instance
        self.on_success_trigger_refresh = on_success_trigger_refresh
        self.require_ticket_scan = require_ticket_scan

        self._temp_action_items_list: List[TempBookActionItem] = []

        self.modal = True
        self.title = ft.Text(self.dialog_title_text, style=ft.TextThemeStyle.HEADLINE_SMALL, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)

        self.total_items_label = ft.Text("Books in List: 0", weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY)
        self.dialog_error_text = ft.Text("", color=ft.Colors.RED_ACCENT_700, visible=False, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)

        scan_field_label = "Scan QR Code"
        scan_field_hint = f"Game({GAME_LENGTH}) + Book({BOOK_LENGTH})"
        if self.require_ticket_scan: # Not used for current new actions but kept for generality
            scan_field_label = "Scan Full Code with Ticket"
            scan_field_hint += f" + Ticket({TICKET_LENGTH})"

        self.scanner_text_field = ft.TextField(
            label=scan_field_label, hint_text=scan_field_hint,
            autofocus=True, height=50, border_radius=8, prefix_icon=ft.Icons.QR_CODE_SCANNER_ROUNDED, expand=True
        )
        self.scan_input_handler = ScanInputHandler(
            scan_text_field=self.scanner_text_field,
            on_scan_complete=self._handle_scan_complete,
            on_scan_error=self._show_dialog_error,
            require_ticket=self.require_ticket_scan
        )

        self.manual_game_no_field = NumberDecimalField(label="Game No.", hint_text=f"{GAME_LENGTH} digits", width=120, max_length=GAME_LENGTH, is_integer_only=True, border_radius=8, height=50)
        self.manual_book_no_field = ft.TextField(label="Book No.", hint_text=f"{BOOK_LENGTH} digits", width=180, max_length=BOOK_LENGTH, border_radius=8, input_filter=ft.InputFilter(r"[0-9]"), height=50)
        self.manual_ticket_no_field = ft.TextField(label="Ticket No.", hint_text=f"{TICKET_LENGTH} digits", width=120, max_length=TICKET_LENGTH, border_radius=8, input_filter=ft.InputFilter(r"[0-9]"), height=50, visible=self.require_ticket_scan)
        self.add_manual_button = ft.Button("Add Manual", icon=ft.Icons.ADD_TO_QUEUE_ROUNDED, on_click=self._handle_manual_add_click, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)))

        self.items_datatable = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Book #", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Details", weight=ft.FontWeight.BOLD, expand=True)), # Details can take more space
                ft.DataColumn(ft.Text("Action Info", weight=ft.FontWeight.BOLD, expand=True)),
                ft.DataColumn(ft.Text("Remove", weight=ft.FontWeight.BOLD), numeric=True),
            ], rows=[], heading_row_height=35, data_row_min_height=40, column_spacing=10, expand=True,
            border=ft.border.all(1, ft.Colors.BLACK12), border_radius=6
        )

        scanner_section = ft.Container(
            ft.Column([ft.Text("Scan QR Code", weight=ft.FontWeight.W_500, size=15, color=ft.Colors.PRIMARY), self.scanner_text_field],
                      spacing=8, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
            padding=ft.padding.symmetric(vertical=10, horizontal=12), border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=ft.border_radius.all(10), bgcolor=ft.Colors.SURFACE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.with_opacity(0.1, ft.Colors.WHITE12),
        )
        manual_entry_row_controls = [self.manual_game_no_field, self.manual_book_no_field]
        if self.require_ticket_scan:
            manual_entry_row_controls.append(self.manual_ticket_no_field)
        manual_entry_row_controls.append(self.add_manual_button)

        manual_section = ft.Container(
            ft.Column([ft.Text("Manual Entry", weight=ft.FontWeight.W_500, size=15, color=ft.Colors.PRIMARY),
                       ft.Row(manual_entry_row_controls, alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.END, spacing=10, expand=True)],
                      spacing=8),
            padding=ft.padding.symmetric(vertical=10, horizontal=12), border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=ft.border_radius.all(10), bgcolor=ft.Colors.SURFACE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Colors.with_opacity(0.1, ft.Colors.WHITE12),
        )
        or_separator = ft.Row(
            [ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
             ft.Container(ft.Text("OR", weight=ft.FontWeight.BOLD, color=ft.Colors.OUTLINE), padding=ft.padding.symmetric(horizontal=8)),
             ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT)],
            alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
        table_scroll_container = ft.Container(
            content=ft.Column([self.items_datatable], scroll=ft.ScrollMode.ADAPTIVE, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
            # border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT), border_radius=ft.border_radius.all(8),
            padding=ft.padding.symmetric(vertical=5), expand=True,
        )

        dialog_content_column = ft.Column(
            [
                scanner_section, or_separator, manual_section,
                self.dialog_error_text,
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                ft.Row([ft.Text("Books Queued for Action:", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.W_600, color=ft.Colors.PRIMARY), self.total_items_label],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                table_scroll_container,
            ],
            spacing=10, expand=True,
        )

        self.content = ft.Container(
            content=dialog_content_column,
            width=dialog_width,
            height=max(600, self.page.height * dialog_height_ratio if self.page.height else 600), # Ensure min height
            padding=ft.padding.symmetric(vertical=12, horizontal=15),
            border_radius=ft.border_radius.all(10)
        )
        self.actions = [
            ft.TextButton("Cancel", on_click=self._handle_cancel_click, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))),
            ft.FilledButton(self.action_button_text, on_click=self._handle_confirm_click, icon=ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)))
        ]
        self.actions_alignment = ft.MainAxisAlignment.END
        self.shape = ft.RoundedRectangleBorder(radius=10)

    def _show_dialog_error(self, message: str):
        self.dialog_error_text.value = message
        self.dialog_error_text.visible = True
        if self.dialog_error_text.page: self.dialog_error_text.update()
        # No full page update here, dialog content update is sufficient

    def _clear_dialog_error(self):
        if self.dialog_error_text.visible:
            self.dialog_error_text.value = ""
            self.dialog_error_text.visible = False
            if self.dialog_error_text.page: self.dialog_error_text.update()

    def _update_dialog_table_and_counts(self):
        self.items_datatable.rows = [
            item.to_datarow(self._remove_item_from_list, self.action_type) for item in self._temp_action_items_list
        ]
        self.total_items_label.value = f"Books in List: {len(self._temp_action_items_list)}"
        if self.items_datatable.page: self.items_datatable.update()
        if self.total_items_label.page: self.total_items_label.update()
        # No full page update here

    def _remove_item_from_list(self, item_to_remove: TempBookActionItem):
        self._temp_action_items_list = [item for item in self._temp_action_items_list if item.unique_key != item_to_remove.unique_key]
        self._update_dialog_table_and_counts()

    def _add_item_to_action_list(self, game_no_str: str, book_no_str: str, ticket_no_str: Optional[str] = None):
        self._clear_dialog_error()
        game_model: Optional[GameModel] = None
        book_model: Optional[BookModel] = None # To store fetched book instance

        try:
            if not (game_no_str and game_no_str.isdigit() and len(game_no_str) == GAME_LENGTH):
                raise ValidationError(f"Game Number must be {GAME_LENGTH} digits.")
            if not (book_no_str and book_no_str.isdigit() and len(book_no_str) == BOOK_LENGTH):
                raise ValidationError(f"Book Number must be {BOOK_LENGTH} digits.")
            # Ticket validation only if required (not for current new actions)
            if self.require_ticket_scan and not (ticket_no_str and ticket_no_str.isdigit() and len(ticket_no_str) == TICKET_LENGTH):
                raise ValidationError(f"Ticket Number must be {TICKET_LENGTH} digits.")

            game_num_int = int(game_no_str)
            with get_db_session() as db:
                game_model = crud_games.get_game_by_game_number(db, game_num_int)
                if not game_model:
                    raise GameNotFoundError(f"Game number '{game_no_str}' not found.")

                # If action is not ADD_NEW, the book must exist.
                if self.action_type != BOOK_ACTION_ADD_NEW:
                    book_model = self.book_service.get_book_by_game_and_book_number(db, game_model.id, book_no_str)
                    if not book_model:
                        raise BookNotFoundError(f"Book '{book_no_str}' for Game '{game_no_str}' not found.")
                    # Eager load game for the book if not already loaded (though get_book_by_game_and_book_number might not load it)
                    if not book_model.game: db.refresh(book_model, ['game'])


                # --- Action-specific validations ---
                if self.action_type == BOOK_ACTION_ADD_NEW:
                    if game_model.is_expired:
                        raise ValidationError(f"Game '{game_model.name}' (No: {game_no_str}) is expired. Cannot add new books.")
                    # Check if book already exists in DB for ADD_NEW
                    existing_book_for_add = self.book_service.get_book_by_game_and_book_number(db, game_model.id, book_no_str)
                    if existing_book_for_add:
                        raise ValidationError(f"Book {game_no_str}-{book_no_str} already exists in the database.")

                elif self.action_type == BOOK_ACTION_FULL_SALE:
                    if not book_model: raise BookNotFoundError("Book must exist for full sale.") # Should be caught above
                    if game_model.is_expired: # Redundant if book_model.game used, but good direct check
                        raise ValidationError(f"Game '{game_model.name}' for Book '{book_no_str}' is expired.")

                    # Check if book is already fully sold out and inactive
                    is_reverse_sold_out = book_model.ticket_order == REVERSE_TICKET_ORDER and book_model.current_ticket_number == -1
                    is_forward_sold_out = book_model.ticket_order == FORWARD_TICKET_ORDER and book_model.current_ticket_number == game_model.total_tickets
                    if (is_reverse_sold_out or is_forward_sold_out) and not book_model.is_active:
                        raise ValidationError(f"Book {game_no_str}-{book_no_str} is already marked as fully sold and inactive.")

                elif self.action_type == BOOK_ACTION_ACTIVATE:
                    if not book_model: raise BookNotFoundError("Book must exist for activation.") # Should be caught above
                    if game_model.is_expired:
                        raise ValidationError(f"Game '{game_model.name}' for Book '{book_no_str}' is expired. Cannot activate.")
                    if book_model.is_active:
                        raise ValidationError(f"Book {game_no_str}-{book_no_str} is already active.")

                    is_reverse_sold_out = book_model.ticket_order == REVERSE_TICKET_ORDER and book_model.current_ticket_number == -1
                    is_forward_sold_out = book_model.ticket_order == FORWARD_TICKET_ORDER and book_model.current_ticket_number == game_model.total_tickets
                    if is_reverse_sold_out or is_forward_sold_out:
                        raise ValidationError(f"Book {game_no_str}-{book_no_str} is finished/sold out. Cannot activate.")


            unique_key_to_add = f"{game_no_str}-{book_no_str}"
            if any(item.unique_key == unique_key_to_add for item in self._temp_action_items_list):
                raise ValidationError(f"Book {unique_key_to_add} is already in the list for this action.")

            # Pass book_model if it was fetched (for FULL_SALE, ACTIVATE)
            temp_item = TempBookActionItem(game_model, book_no_str, book_model_ref=book_model, ticket_number_str=ticket_no_str)
            self._temp_action_items_list.insert(0, temp_item)
            self._update_dialog_table_and_counts()

            self.manual_game_no_field.clear()
            self.manual_book_no_field.value = ""
            if self.manual_book_no_field.page: self.manual_book_no_field.update()
            if self.require_ticket_scan and self.manual_ticket_no_field:
                self.manual_ticket_no_field.value = ""
                if self.manual_ticket_no_field.page: self.manual_ticket_no_field.update()

            if self.scan_input_handler: self.scan_input_handler.focus_input()

        except (GameNotFoundError, BookNotFoundError, ValidationError, DatabaseError) as e:
            self._show_dialog_error(str(e.message if hasattr(e, 'message') else e))
        except ValueError:
            self._show_dialog_error(f"Invalid Game Number format. Must be {GAME_LENGTH} digits.")
        except Exception as ex_unhandled:
            self._show_dialog_error(f"Unexpected error: {type(ex_unhandled).__name__} - {ex_unhandled}")


    def _handle_scan_complete(self, parsed_data: Dict[str, str]):
        game_no = parsed_data.get('game_no', '')
        book_no = parsed_data.get('book_no', '')
        ticket_no = parsed_data.get('ticket_no') if self.require_ticket_scan else None
        self._add_item_to_action_list(game_no, book_no, ticket_no)

    def _handle_manual_add_click(self, e: ft.ControlEvent):
        game_no_str = self.manual_game_no_field.get_value_as_str()
        book_no_str = self.manual_book_no_field.value.strip() if self.manual_book_no_field.value else ""
        ticket_no_str = None
        if self.require_ticket_scan and self.manual_ticket_no_field:
            ticket_no_str = self.manual_ticket_no_field.value.strip() if self.manual_ticket_no_field.value else ""

        self._add_item_to_action_list(game_no_str, book_no_str, ticket_no_str)

    def _handle_confirm_click(self, e: ft.ControlEvent):
        self._clear_dialog_error()
        if not self._temp_action_items_list:
            self._show_dialog_error("No books in the list to process.")
            return

        items_to_submit = [item.to_submission_dict() for item in self._temp_action_items_list]

        # Show a loading indicator on the button
        confirm_button = self.actions[1] # Assuming it's the second button
        original_button_text = confirm_button.text
        confirm_button.text = "Processing..."
        confirm_button.disabled = True
        if confirm_button.page: confirm_button.update()

        try:
            with get_db_session() as db:
                success_count, failure_count, error_messages = self.on_confirm_batch_callback(
                    db, items_to_submit, self.current_user
                )

            self.page.close(self)

            final_message = f"{success_count} book(s) processed successfully."
            if failure_count > 0:
                final_message += f" {failure_count} book(s) failed."
            if error_messages:
                print(f"Book Action Dialog - Batch Errors for '{self.dialog_title_text}': {error_messages}")
                final_message += " (See console for details on failures)."

            self.page.open(ft.SnackBar(ft.Text(final_message), open=True, duration=7000 if error_messages else 4000))
            if success_count > 0 and self.on_success_trigger_refresh:
                self.on_success_trigger_refresh()

        except Exception as ex_batch:
            self._show_dialog_error(f"Error during batch processing: {ex_batch}")
            # Re-enable button on error
            confirm_button.text = original_button_text
            confirm_button.disabled = False
            if confirm_button.page: confirm_button.update()


    def _handle_cancel_click(self, e: ft.ControlEvent):
        self.page.close(self)

    def open_dialog(self):
        self.page.dialog = self
        self.page.open(self)
        if self.scan_input_handler:
            threading.Thread(target=self._delayed_focus, daemon=True).start()


    def _delayed_focus(self):
        time.sleep(0.15) # Slightly longer delay
        if self.scan_input_handler and self.scanner_text_field.page:
            self.scan_input_handler.focus_input()