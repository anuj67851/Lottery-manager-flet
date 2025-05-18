import flet as ft
from typing import List, Optional, Callable

from app.constants import ADMIN_DASHBOARD_ROUTE, GAME_LENGTH, MIN_REQUIRED_SCAN_LENGTH, BOOK_LENGTH, QR_TOTAL_LENGTH
from app.core.models import User, Game as GameModel
from app.services.book_service import BookService
from app.services.game_service import GameService # To validate game numbers and get details
from app.data.database import get_db_session
from app.core.exceptions import ValidationError, DatabaseError, GameNotFoundError
from app.data import crud_games # For direct game fetching by number
from app.ui.components.common.appbar_factory import create_appbar
from app.ui.components.common.search_bar_component import SearchBarComponent
from app.ui.components.tables.books_table import BooksTable
from app.ui.components.widgets import NumberDecimalField


class TempBookEntry:
    def __init__(self, game_number_str: str, book_number_str: str, game_name: str, game_price_formatted: str, game_id: int):
        self.game_number_str = game_number_str
        self.book_number_str = book_number_str
        self.game_name = game_name
        self.game_price_formatted = game_price_formatted # Should be integer string like "$1"
        self.game_id = game_id
        self.unique_key = f"{game_number_str}-{book_number_str}"

    def to_datarow(self, on_remove_callback: Callable[['TempBookEntry'], None]) -> ft.DataRow:
        return ft.DataRow(cells=[
            ft.DataCell(ft.Text(f"{self.game_number_str} - {self.book_number_str}")),
            ft.DataCell(ft.Text(f"{self.game_name} ({self.game_price_formatted})")),
            ft.DataCell(ft.IconButton(ft.Icons.REMOVE_CIRCLE_OUTLINE, icon_color=ft.Colors.RED_ACCENT_700,
                                      on_click=lambda e: on_remove_callback(self), tooltip="Remove from list"))
        ])

    def __repr__(self):
        return f"BookEntry(game_number_str={self.game_number_str}, book_number_str={self.book_number_str}, game_name={self.game_name}, game_price_formatted={self.game_price_formatted}, game_id={self.game_id})"

class BookManagementView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user: User, license_status: bool,
                 previous_view_route: str = ADMIN_DASHBOARD_ROUTE,
                 previous_view_params: dict = None, **params):
        super().__init__(expand=True, padding=0)
        self.page = page
        self.router = router
        self.current_user = current_user
        self.license_status = license_status
        self.previous_view_route = previous_view_route
        self.previous_view_params = previous_view_params if previous_view_params is not None else {}

        self.book_service = BookService()
        self.game_service = GameService()

        self.total_books_widget = ft.Text("", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD)
        self.active_books_widget = ft.Text("", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)
        self.inactive_books_widget = ft.Text("", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_700)

        self.books_table_component = BooksTable(
            page=self.page,
            book_service=self.book_service,
            on_data_changed_stats=self._handle_table_data_stats_change
        )
        self.search_bar = SearchBarComponent(
            on_search_changed=self._on_search_term_changed,
            label="Search Books (Game No., Book No., Game Name)"
        )

        self.page.appbar = create_appbar(
            page=self.page, router=self.router, title_text="Admin > Book Management",
            current_user=self.current_user, license_status=self.license_status,
            leading_widget=ft.IconButton(ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED, tooltip="Go Back", icon_color=ft.Colors.WHITE, on_click=self._go_back)
        )
        self.content = self._build_body()
        self.books_table_component.refresh_data_and_ui()

    def _go_back(self, e):
        nav_params = {**self.previous_view_params}
        if "current_user" not in nav_params and self.current_user: nav_params["current_user"] = self.current_user
        if "license_status" not in nav_params and self.license_status is not None: nav_params["license_status"] = self.license_status
        self.router.navigate_to(self.previous_view_route, **nav_params)

    def _on_search_term_changed(self, search_term: str):
        self.books_table_component.refresh_data_and_ui(search_term=search_term)

    def _handle_table_data_stats_change(self, total: int, active: int, inactive: int):
        self.total_books_widget.value = f"Total Books: {total}"
        self.active_books_widget.value = f"Active: {active}"
        self.inactive_books_widget.value = f"Inactive: {inactive}"
        if self.page and self.page.controls: self.page.update()

    def _build_body(self) -> ft.Container:
        stats_row = ft.Row(
            [self.total_books_widget, ft.VerticalDivider(), self.active_books_widget, ft.VerticalDivider(), self.inactive_books_widget],
            alignment=ft.MainAxisAlignment.START, spacing=15
        )
        actions_row = ft.Row(
            [
                self.search_bar,
                ft.FilledButton("Add New Books", icon=ft.Icons.LIBRARY_ADD_ROUNDED, on_click=self._open_add_books_dialog, height=48)
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=15
        )
        card_content = ft.Column(
            [
                ft.Text("Book Inventory & Management", style=ft.TextThemeStyle.HEADLINE_SMALL, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.LEFT),
                ft.Divider(height=10), stats_row, ft.Divider(height=20), actions_row,
                ft.Divider(height=15, color=ft.Colors.TRANSPARENT), self.books_table_component,
            ], spacing=15, expand=True
        )
        TARGET_CARD_MAX_WIDTH = 1100; MIN_CARD_WIDTH = 360; SIDE_PADDING = 20
        page_width_available = self.page.width if self.page.width and self.page.width > (2 * SIDE_PADDING) else (MIN_CARD_WIDTH + 2 * SIDE_PADDING)
        card_effective_width = min(TARGET_CARD_MAX_WIDTH, page_width_available - (2 * SIDE_PADDING))
        card_effective_width = max(MIN_CARD_WIDTH, card_effective_width)
        if page_width_available <= (2 * SIDE_PADDING): card_effective_width = max(10, page_width_available - 2)
        elif card_effective_width <= 0: card_effective_width = MIN_CARD_WIDTH

        main_card = ft.Card(
            content=ft.Container(content=card_content, padding=20, border_radius=ft.border_radius.all(10)),
            elevation=2, width=card_effective_width
        )
        return ft.Container(content=main_card, alignment=ft.alignment.top_center, padding=20, expand=True)

    def _open_add_books_dialog(self, e):
        temp_books_to_add: List[TempBookEntry] = []

        total_added_label = ft.Text("Total Books in List: 0", weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY)
        dialog_error_text = ft.Text("", color=ft.Colors.RED_ACCENT_700, visible=False, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)

        def _update_dialog_ui_elements():
            """Helper to update specific parts of the dialog that change often."""
            if self.page and self.page.dialog:
                total_added_label.update()
                dialog_error_text.update()
                dialog_books_table.update()
                # self.page.update() # Avoid full page update if only dialog content changes

        def _handle_scanner_input_change(ev: ft.ControlEvent):
            scanner_field = ev.control
            current_value = scanner_field.value.strip() if scanner_field.value else ""
            if len(current_value) >= QR_TOTAL_LENGTH:
                self._process_scanner_input(
                    scanner_field, temp_books_to_add, dialog_books_table,
                    dialog_error_text, total_added_label
                ) # This will clear and refocus internally

        scanner_input_field = ft.TextField(
            label="Scan Full Book Code",
            hint_text=f"Scanned input (auto-submits at {QR_TOTAL_LENGTH} chars)",
            on_change=_handle_scanner_input_change,
            on_submit=lambda ev: self._process_scanner_input( # Fallback if Enter is pressed early
                ev.control, temp_books_to_add, dialog_books_table,
                dialog_error_text, total_added_label
            ),
            autofocus=True, height=50, border_radius=8, prefix_icon=ft.Icons.QR_CODE_SCANNER_ROUNDED, expand=True
        )

        def _add_manual_entry_handler(ev):
            self._process_manual_input(
                manual_game_no_field, manual_book_no_field, temp_books_to_add,
                dialog_books_table, dialog_error_text, total_added_label,
                manual_game_no_field
            )

        manual_game_no_field = NumberDecimalField(label="Game No.", hint_text="3 digits", width=120, max_length=GAME_LENGTH, is_integer_only=True, border_radius=8, height=50)
        manual_book_no_field = ft.TextField(label="Book No.", hint_text="7 digits", width=210, max_length=BOOK_LENGTH, border_radius=8, input_filter=ft.InputFilter(r"[0-9]"), height=50, on_submit=_add_manual_entry_handler)

        dialog_books_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Game-Book", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Details", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Action", weight=ft.FontWeight.BOLD), numeric=True),
            ], rows=[], heading_row_height=40, data_row_min_height=45, column_spacing=20, expand=True, width=500,
        )

        add_manual_button = ft.Button("Add Manual", icon=ft.Icons.ADD_TO_QUEUE_ROUNDED, on_click=_add_manual_entry_handler, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)))

        table_scroll_container = ft.Container(
            content=ft.Column([dialog_books_table], scroll=ft.ScrollMode.ADAPTIVE),
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT), border_radius=ft.border_radius.all(8),
            padding=ft.padding.all(8), expand=True, # Make table container expand vertically
        )

        scanner_section = ft.Container(
            ft.Column([ft.Text("Scan Book Barcode", weight=ft.FontWeight.W_500, size=16, color=ft.Colors.PRIMARY), scanner_input_field],
                      spacing=8, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
            padding=ft.padding.symmetric(vertical=12, horizontal=16), border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=ft.border_radius.all(12), bgcolor=ft.Colors.SURFACE,
        )
        manual_section = ft.Container(
            ft.Column([ft.Text("Manual Entry", weight=ft.FontWeight.W_500, size=16, color=ft.Colors.PRIMARY),
                       ft.Row([manual_game_no_field, manual_book_no_field, add_manual_button],
                              alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.END, spacing=10)],
                      spacing=8),
            padding=ft.padding.symmetric(vertical=12, horizontal=16), border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=ft.border_radius.all(12), bgcolor=ft.Colors.SURFACE,
        )
        or_separator = ft.Row(
            [ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
             ft.Container(ft.Text("OR", weight=ft.FontWeight.BOLD, color=ft.Colors.OUTLINE), padding=ft.padding.symmetric(horizontal=10)),
             ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT)],
            alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

        dialog_content_column = ft.Column(
            [
                ft.Text("Add New Books", style=ft.TextThemeStyle.HEADLINE_MEDIUM, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY, text_align=ft.TextAlign.CENTER),
                ft.Text("Scan barcode or manually enter book information", style=ft.TextThemeStyle.BODY_LARGE, color=ft.Colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER),
                ft.Divider(height=15, thickness=1),
                scanner_section, or_separator, manual_section,
                dialog_error_text, # Display error messages here
                ft.Divider(height=15, color=ft.Colors.TRANSPARENT),
                ft.Row([ft.Text("Books to be Added:", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.W_600, color=ft.Colors.PRIMARY), total_added_label],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                table_scroll_container,
            ],
            spacing=12, expand=True,
        )

        def _confirm_add_books_handler(ev):
            dialog_error_text.value = ""; dialog_error_text.visible = False # Clear previous errors
            _update_dialog_ui_elements()

            if not temp_books_to_add:
                dialog_error_text.value = "No books in the list to add."
                dialog_error_text.visible = True
                _update_dialog_ui_elements()
                return

            books_for_service = [{"game_number_str": b.game_number_str, "book_number_str": b.book_number_str, "game_id": b.game_id} for b in temp_books_to_add]
            try:
                with get_db_session() as db:
                    created_books, service_errors = self.book_service.add_books_in_batch(db, books_for_service) # Expecting (created_list, error_list)

                if self.page.dialog: self.page.close(self.page.dialog)

                success_msg = f"{len(created_books)} books added successfully."
                if service_errors:
                    success_msg += f" {len(service_errors)} books had issues (see console/logs)."
                    # For more detailed UI feedback, you might show these errors in another dialog or a persistent area.
                    print(f"Batch Add Book Errors: {service_errors}") # Log errors

                self.page.open(ft.SnackBar(content=ft.Text(success_msg), action="OK", open=True))
                self.books_table_component.refresh_data_and_ui()

            except (ValidationError, DatabaseError) as ex_service: # If add_books_in_batch itself raises before returning partial
                dialog_error_text.value = f"Service Error: {ex_service.message}"
                dialog_error_text.visible = True
            except Exception as ex_general:
                dialog_error_text.value = f"Unexpected Error: {ex_general}"
                dialog_error_text.visible = True
            _update_dialog_ui_elements()


        cancel_button = ft.TextButton("Cancel", on_click=lambda _: self.page.close(self.page.dialog), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)))
        confirm_button = ft.FilledButton("Confirm & Add Books", on_click=_confirm_add_books_handler, icon=ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)))

        add_books_dialog = ft.AlertDialog(
            modal=True, title=None,
            content=ft.Container(
                content=dialog_content_column,
                width=550, # Increased width for better layout
                height=self.page.height * 0.9 if self.page.height and self.page.height > 700 else 700, # Max height
                padding=ft.padding.symmetric(vertical=15, horizontal=20),
                border_radius=ft.border_radius.all(12)
            ),
            actions=[cancel_button, confirm_button],
            actions_alignment=ft.MainAxisAlignment.END, shape=ft.RoundedRectangleBorder(radius=12)
        )
        self.page.dialog = add_books_dialog
        self.page.open(self.page.dialog)

    def _update_dialog_table(self, temp_books_list: List[TempBookEntry], table_widget: ft.DataTable, error_widget: ft.Text, count_label: ft.Text):
        table_widget.rows = [b.to_datarow(lambda book_to_remove: self._remove_book_from_temp_list(book_to_remove, temp_books_list, table_widget, error_widget, count_label)) for b in temp_books_list]
        count_label.value = f"Total Books in List: {len(temp_books_list)}"
        if self.page and self.page.dialog:
            error_widget.update() # Explicitly update error widget
            count_label.update()
            table_widget.update()
            # self.page.update() # Update the whole page if dialog content has changed significantly.

    def _remove_book_from_temp_list(self, book_entry: TempBookEntry, temp_books_list: List[TempBookEntry], table_widget: ft.DataTable, error_widget: ft.Text, count_label: ft.Text):
        temp_books_list.remove(book_entry)
        self._update_dialog_table(temp_books_list, table_widget, error_widget, count_label)

    def _add_to_temp_books_list(self, game_number_str: str, book_number_str: str, temp_books_list: List[TempBookEntry],
                                table_widget: ft.DataTable, error_widget: ft.Text, count_label: ft.Text,
                                error_focus_target: Optional[ft.Control] = None, success_focus_target: Optional[ft.Control] = None):
        error_widget.value = ""; error_widget.visible = False
        if error_widget.page: error_widget.update() # Clear previous error visually

        game_model: Optional[GameModel] = None
        try:
            if not (game_number_str and game_number_str.isdigit() and len(game_number_str) == 3):
                raise ValidationError("Game Number must be 3 digits.")
            if not (book_number_str and book_number_str.isdigit() and len(book_number_str) == 7):
                raise ValidationError("Book Number must be 7 digits.")

            game_num_int = int(game_number_str)
            with get_db_session() as db: game_model = crud_games.get_game_by_game_number(db, game_num_int)

            if not game_model: raise GameNotFoundError(f"Game number '{game_number_str}' not found.")
            if game_model.is_expired: raise ValidationError(f"Game '{game_model.name}' (No: {game_number_str}) is expired.")
            if any(b.unique_key == f"{game_number_str}-{book_number_str}" for b in temp_books_list):
                raise ValidationError(f"Book {game_number_str}-{book_number_str} is already in the list.")

            game_price_display = f"${game_model.price}"
            temp_entry = TempBookEntry(game_number_str, book_number_str, game_model.name, game_price_display, game_model.id)
            temp_books_list.insert(0, temp_entry)
            self._update_dialog_table(temp_books_list, table_widget, error_widget, count_label)
            if success_focus_target and success_focus_target.page: success_focus_target.focus()

        except (GameNotFoundError, ValidationError, DatabaseError) as e:
            error_widget.value = str(e.message if hasattr(e, 'message') else e); error_widget.visible = True
            if error_focus_target and error_focus_target.page : error_focus_target.focus()
        except ValueError: # int conversion error
            error_widget.value = "Invalid Game Number format (must be 3 digits)."; error_widget.visible = True
            if error_focus_target and hasattr(error_focus_target, 'is_integer_only') and error_focus_target.page : error_focus_target.focus() # Focus game_no field
        except Exception as ex_unhandled:
            error_widget.value = f"Unexpected error: {ex_unhandled}"; error_widget.visible = True

        if error_widget.page: error_widget.update() # Ensure error text is displayed
        if self.page and self.page.dialog: self.page.update() # Update dialog for error visibility

    def _process_scanner_input(self, input_field: ft.TextField, temp_books_list: List[TempBookEntry], table_widget: ft.DataTable, error_widget: ft.Text, count_label: ft.Text):
        scan_value = input_field.value.strip() if input_field.value else ""
        # Clear field immediately for next scan
        input_field.value = ""
        if input_field.page: input_field.update() # Update the visual of the input field
        # Focus will be handled by _add_to_temp_books_list or fallback here

        if len(scan_value) < MIN_REQUIRED_SCAN_LENGTH:
            error_widget.value = f"Scanned input too short (min {MIN_REQUIRED_SCAN_LENGTH} chars for Book)."
            error_widget.visible = True
            if error_widget.page: error_widget.update()
            if input_field.page: input_field.focus()
            if self.page and self.page.dialog: self.page.update()
            return

        game_no_str = scan_value[:GAME_LENGTH]
        book_no_str = scan_value[GAME_LENGTH:(GAME_LENGTH + BOOK_LENGTH)]
        self._add_to_temp_books_list(game_no_str, book_no_str, temp_books_list, table_widget, error_widget, count_label, error_focus_target=input_field, success_focus_target=input_field)

    def _process_manual_input(self, game_field: NumberDecimalField, book_field: ft.TextField, temp_books_list: List[TempBookEntry], table_widget: ft.DataTable, error_widget: ft.Text, count_label: ft.Text, manual_field_ref: ft.TextField):
        game_no_str = game_field.get_value_as_str()
        book_no_str = book_field.value.strip() if book_field.value else ""

        # Determine which field likely caused error for focus
        error_focus = game_field # Default to game field
        if game_no_str and len(game_no_str) == GAME_LENGTH and game_no_str.isdigit():
            error_focus = book_field # If game number seems okay, error is likely with book number

        self._add_to_temp_books_list(game_no_str, book_no_str, temp_books_list, table_widget, error_widget, count_label, error_focus_target=error_focus, success_focus_target=manual_field_ref)

        if not error_widget.visible or not error_widget.value: # If successfully added
            game_field.clear()
            book_field.value = ""
            if book_field.page: book_field.update()
            if manual_field_ref.page: manual_field_ref.focus() # Focus scanner after successful manual add