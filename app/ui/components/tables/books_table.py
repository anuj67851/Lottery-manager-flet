from typing import List, Callable, Optional, Dict, Any
import flet as ft
import datetime

from app.core import ValidationError, DatabaseError
from app.core.models import Book
from app.services.book_service import BookService, BookNotFoundError
from app.data.database import get_db_session
from app.ui.components.common.paginated_data_table import PaginatedDataTable
from app.ui.components.common.dialog_factory import create_confirmation_dialog, create_form_dialog
from app.ui.components.widgets import NumberDecimalField # For edit dialog potentially
from app.constants import REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER

import logging
logger = logging.getLogger(__name__)
class BooksTable(PaginatedDataTable[Book]):
    def __init__(self, page: ft.Page, book_service: BookService,
                 on_data_changed_stats: Optional[Callable[[int, int, int], None]] = None):

        self.book_service = book_service
        self._on_data_changed_stats = on_data_changed_stats
        self.current_action_book: Optional[Book] = None
        self._books_with_sales_ids: set[int] = set()

        column_definitions: List[Dict[str, Any]] = [
            {"key": "id", "label": "ID", "sortable": True, "numeric": False, "searchable": False},
            {"key": "game_number", "label": "Game No.", "sortable": True, "numeric": True, "searchable": True,
             "display_formatter": lambda val, item: ft.Text(str(item.game.game_number) if item.game else "N/A")},
            {"key": "book_number", "label": "Book No.", "sortable": True, "numeric": False, "searchable": True},
            {"key": "game_name", "label": "Game Name", "sortable": False, "numeric": False, "searchable": True,
             "display_formatter": lambda val, item: ft.Text(str(item.game.name) if item.game else "N/A")},
            {"key": "game_price", "label": "Price ($)", "sortable": False, "numeric": True, # Game.price is in CENTS
             "display_formatter": lambda val, item: ft.Text(f"{(item.game.price / 100.0):.2f}" if item.game and item.game.price is not None else "N/A")},
            {"key": "game_total_tickets", "label": "Total Tkts (Game)", "sortable": False, "numeric": True, "searchable": False,
             "display_formatter": lambda val, item: ft.Text(str(item.game.total_tickets) if item.game else "N/A")},
            {"key": "current_ticket_number", "label": "Curr. Ticket", "sortable": True, "numeric": True},
            {"key": "ticket_order", "label": "Order", "sortable": True, "numeric": False,
             "display_formatter": lambda val: ft.Text(str(val).capitalize())},
            {"key": "is_active", "label": "Status", "sortable": True, "numeric": False,
             "display_formatter": self._format_status_cell},
            {"key": "activate_date", "label": "Activated", "sortable": True, "numeric": False,
             "display_formatter": lambda val: ft.Text(val.strftime("%Y-%m-%d") if val else "-")},
            {"key": "finish_date", "label": "Finished", "sortable": True, "numeric": False,
             "display_formatter": lambda val: ft.Text(val.strftime("%Y-%m-%d") if val else "-")},
        ]

        super().__init__(
            page=page,
            fetch_all_data_func=self._fetch_books_data,
            column_definitions=column_definitions,
            action_cell_builder=self._build_action_cell,
            rows_per_page=15,
            initial_sort_key="id",
            initial_sort_ascending=False,
        )

    def _fetch_books_data(self, db_session) -> List[Book]:
        return self.book_service.get_all_books_with_details(db_session)

    def _format_status_cell(self, is_active_val: bool, item: Book) -> ft.Control:
        if is_active_val:
            return ft.Text("Active", color=ft.Colors.GREEN_700, weight=ft.FontWeight.BOLD)
        else:
            if item.finish_date:
                return ft.Text("Finished", color=ft.Colors.BLUE_GREY_400)
            return ft.Text("Inactive", color=ft.Colors.RED_ACCENT_700)

    def _filter_and_sort_displayed_data(self, search_term: str = ""):
        super()._filter_and_sort_displayed_data(search_term)
        if self._on_data_changed_stats and self._all_unfiltered_data is not None:
            total_books = len(self._all_unfiltered_data)
            active_books = sum(1 for book in self._all_unfiltered_data if book.is_active)
            inactive_books = total_books - active_books
            self._on_data_changed_stats(total_books, active_books, inactive_books)

    def _build_action_cell(self, book: Book, table_instance: PaginatedDataTable) -> ft.DataCell:
        actions = []
        edit_button = ft.IconButton(
            ft.Icons.EDIT_ROUNDED, tooltip="Edit Book", icon_color=ft.Colors.PRIMARY, icon_size=18,
            on_click=lambda e, b=book: self._open_edit_book_dialog(b)
        )
        actions.append(edit_button)

        if book.is_active:
            toggle_button = ft.IconButton(
                ft.Icons.TOGGLE_ON_ROUNDED, tooltip="Deactivate Book", icon_color=ft.Colors.RED_ACCENT_700, icon_size=20,
                on_click=lambda e, b=book: self._confirm_toggle_active_status(b, False)
            )
        else:
            can_activate = True
            if book.game and ((book.current_ticket_number == -1 and book.ticket_order == REVERSE_TICKET_ORDER) or \
                              (book.current_ticket_number == book.game.total_tickets and book.ticket_order == FORWARD_TICKET_ORDER)):
                can_activate = False

            toggle_button = ft.IconButton(
                ft.Icons.TOGGLE_OFF_OUTLINED,
                tooltip="Activate Book" if can_activate else "Cannot activate (book is finished)",
                icon_color=ft.Colors.GREEN_700 if can_activate else ft.Colors.GREY_400,
                icon_size=18,
                disabled=not can_activate,
                on_click=lambda e, b=book: self._confirm_toggle_active_status(b, True) if can_activate else None
            )
        actions.append(toggle_button)

        can_delete = False
        if not book.is_active and book.id not in self._books_with_sales_ids:
            can_delete = True

        delete_button = ft.IconButton(
            ft.Icons.DELETE_FOREVER_ROUNDED,
            tooltip="Delete Book" if can_delete else "Cannot delete (book is active or has sales entries)",
            icon_color=ft.Colors.RED_700 if can_delete else ft.Colors.GREY_400,
            icon_size=18,
            disabled=not can_delete,
            on_click=lambda e, b=book: self._confirm_delete_book_dialog(b) if can_delete else None
        )
        actions.append(delete_button)
        return ft.DataCell(ft.Row(actions, spacing=-5, alignment=ft.MainAxisAlignment.END))

    def _confirm_toggle_active_status(self, book: Book, to_active: bool):
        self.current_action_book = book
        action_word = "activate" if to_active else "deactivate"
        title_color = ft.Colors.GREEN_700 if to_active else ft.Colors.RED_700

        if to_active and book.game and book.game.is_expired:
            self.show_error_snackbar(f"Cannot activate book for expired game '{book.game.name}'.")
            return

        dialog_content = ft.Text(f"Are you sure you want to {action_word} Book No. {book.book_number} for Game No. {book.game.game_number if book.game else 'N/A'}?")
        confirm_dialog = create_confirmation_dialog(
            title_text=f"Confirm {action_word.capitalize()}", title_color=title_color, content_control=dialog_content,
            on_confirm=self._handle_toggle_active_confirmed,
            on_cancel=lambda e: self.close_dialog_and_refresh(self.page.dialog), # type: ignore
            confirm_button_text=action_word.capitalize(),
            confirm_button_style=ft.ButtonStyle(bgcolor=title_color, color=ft.Colors.WHITE)
        )
        self.page.dialog = confirm_dialog; self.page.open(self.page.dialog)

    def _handle_toggle_active_confirmed(self, e=None):
        if not self.current_action_book: return
        book_to_toggle = self.current_action_book; is_activating = not book_to_toggle.is_active
        current_dialog = self.page.dialog
        try:
            with get_db_session() as db:
                if is_activating: self.book_service.activate_book(db, book_to_toggle.id)
                else: self.book_service.deactivate_book(db, book_to_toggle.id)
            action_word_past = "activated" if is_activating else "deactivated"
            self.close_dialog_and_refresh(current_dialog, f"Book {book_to_toggle.book_number} {action_word_past}.")
        except (BookNotFoundError, ValidationError, DatabaseError) as ex:
            self.show_error_snackbar(str(ex.message if hasattr(ex, 'message') else ex))
            self.close_dialog_and_refresh(current_dialog)
        except Exception as ex_general:
            self.show_error_snackbar(f"Unexpected error: {ex_general}")
            self.close_dialog_and_refresh(current_dialog)
        finally: self.current_action_book = None

    def _open_edit_book_dialog(self, book: Book):
        self.current_action_book = book
        has_sales = False
        try:
            with get_db_session() as db: has_sales = self.book_service.has_book_any_sales(db, book.id)
        except Exception as e:
            self.show_error_snackbar(f"Error checking book sales status: {e}"); return

        book_number_field = ft.TextField(label="Book Number (7 digits)", value=book.book_number, border_radius=8, max_length=7)
        current_ticket_field = ft.TextField(label="Ticket Number (3 digits)", value=str(book.current_ticket_number), border_radius=8, max_length=3) # Value must be string
        ticket_order_options = [ft.dropdown.Option(order, order.capitalize()) for order in [REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER]]
        ticket_order_dropdown = ft.Dropdown(label="Ticket Order", options=ticket_order_options, value=book.ticket_order, border_radius=8, disabled=has_sales)
        error_text_edit = ft.Text(visible=False, color=ft.Colors.RED_700)
        restriction_info_text = ft.Text("Ticket Order cannot be changed because this book has sales entries.", italic=True, size=11, color=ft.Colors.ORANGE_ACCENT_700, visible=has_sales)

        controls = []
        game_info_texts = []
        if book.game:
            game_info_texts.append(ft.Text(f"Game Number: {book.game.game_number}", size=14, weight=ft.FontWeight.W_500))
            game_info_texts.append(ft.Text(f"Game Price: ${(book.game.price / 100.0):.2f}", size=14, weight=ft.FontWeight.W_500)) # Display game price in dollars
            game_info_texts.append(ft.Text(f"Total Tickets: {book.game.total_tickets}", size=14, weight=ft.FontWeight.W_500))
            game_info_texts.append(ft.Text(f"Game Name: {book.game.name}", size=14, weight=ft.FontWeight.W_500, overflow=ft.TextOverflow.ELLIPSIS, width=350))

        if game_info_texts:
            controls.append(ft.Column(game_info_texts, spacing=5))
            controls.append(ft.Container(height=10))

        controls.extend([book_number_field, current_ticket_field, restriction_info_text, ticket_order_dropdown, error_text_edit])

        form_column = ft.Column(controls, tight=True, spacing=15, scroll=ft.ScrollMode.AUTO)

        def _save_edits_handler(e):
            if not self.current_action_book: return
            error_text_edit.value = ""; error_text_edit.visible = False
            new_book_num = book_number_field.value.strip() if book_number_field.value else None
            new_ticket_num_str = current_ticket_field.value.strip() if current_ticket_field.value else None # Keep as str for service
            new_order = ticket_order_dropdown.value if not ticket_order_dropdown.disabled else None
            try:
                # Validation for book_number and ticket_number format will be in service
                with get_db_session() as db:
                    self.book_service.edit_book(db, self.current_action_book.id, new_book_num, new_ticket_num_str, new_order)
                self.close_dialog_and_refresh(self.page.dialog, f"Book {new_book_num or self.current_action_book.book_number} updated.") # type: ignore
            except (ValidationError, DatabaseError, BookNotFoundError) as ex:
                error_text_edit.value = str(ex.message if hasattr(ex, 'message') else ex); error_text_edit.visible = True
            except Exception as ex_general:
                error_text_edit.value = f"Unexpected error: {ex_general}"; error_text_edit.visible = True
            if self.page: self.page.update()

        edit_dialog = create_form_dialog(
            page=self.page, title_text=f"Edit Book: {book.book_number} (Game: {book.game.game_number if book.game else 'N/A'})",
            form_content_column=form_column, on_save_callback=_save_edits_handler,
            on_cancel_callback=lambda ev: self.close_dialog_and_refresh(self.page.dialog), # type: ignore
            save_button_text="Save Changes", min_width=420 # Slightly wider for game info
        )
        self.page.dialog = edit_dialog; self.page.open(self.page.dialog)

    def refresh_data_and_ui(self, search_term: Optional[str] = None):
        if search_term is None: search_term = self._last_search_term
        else: self._last_search_term = search_term
        try:
            with get_db_session() as db:
                self._all_unfiltered_data = self.fetch_all_data_func(db)
                self._books_with_sales_ids = self.book_service.get_ids_of_books_with_sales(db)
            self._current_page_number = 1
            self._filter_and_sort_displayed_data(search_term)
        except Exception as e:
            logger.error(f"Error refreshing data for BooksTable: {e}", exc_info=True)
            if self.page: self.page.open(ft.SnackBar(ft.Text(f"Error loading book data: {type(e).__name__}"), open=True, bgcolor=ft.Colors.ERROR))

    def _confirm_delete_book_dialog(self, book: Book):
        self.current_action_book = book
        if book.is_active: self.show_error_snackbar("Action aborted: Book is currently active."); return
        try:
            with get_db_session() as db:
                if self.book_service.has_book_any_sales(db, book.id):
                    self.show_error_snackbar("Action aborted: Book has sales entries."); return
        except Exception as e_check_dialog:
            self.show_error_snackbar(f"Error checking book status: {e_check_dialog}"); return

        dialog_content = ft.Text(f"Are you sure you want to permanently delete Book No. {book.book_number} for Game No. {book.game.game_number if book.game else 'N/A'}? This action cannot be undone.")
        confirm_dialog = create_confirmation_dialog(
            title_text="Confirm Delete Book", title_color=ft.Colors.RED_900, content_control=dialog_content,
            on_confirm=self._handle_delete_book_confirmed,
            on_cancel=lambda e: self.close_dialog_and_refresh(self.page.dialog), # type: ignore
            confirm_button_text="Delete Permanently",
            confirm_button_style=ft.ButtonStyle(bgcolor=ft.Colors.RED_900, color=ft.Colors.WHITE)
        )
        self.page.dialog = confirm_dialog; self.page.open(self.page.dialog)

    def _handle_delete_book_confirmed(self, e=None):
        if not self.current_action_book: return
        book_to_delete = self.current_action_book; current_dialog = self.page.dialog
        try:
            with get_db_session() as db: self.book_service.delete_book(db, book_to_delete.id)
            self.close_dialog_and_refresh(current_dialog, f"Book {book_to_delete.book_number} deleted successfully.") # Use book_number directly
        except (BookNotFoundError, ValidationError, DatabaseError) as ex:
            self.show_error_snackbar(str(ex.message if hasattr(ex, 'message') and ex.message else ex))
            self.close_dialog_and_refresh(current_dialog)
        except Exception as ex_general:
            self.show_error_snackbar(f"Unexpected error deleting book: {ex_general}")
            self.close_dialog_and_refresh(current_dialog)
        finally: self.current_action_book = None