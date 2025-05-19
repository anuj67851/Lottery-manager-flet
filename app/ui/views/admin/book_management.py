import flet as ft
from typing import List, Dict, Tuple, Any

from sqlalchemy.orm import Session # For type hinting callback

from app.constants import ADMIN_DASHBOARD_ROUTE, BOOK_ACTION_ADD_NEW
from app.core.models import User
from app.services.book_service import BookService
from app.services.game_service import GameService
from app.ui.components.common.appbar_factory import create_appbar
from app.ui.components.common.search_bar_component import SearchBarComponent
from app.ui.components.tables.books_table import BooksTable
from app.ui.components.dialogs.book_action_dialog import BookActionDialog # New generic dialog

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
        self.game_service = GameService() # Needed for BookActionDialog

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
            page=self.page, router=self.router, title_text=f"{self.current_user.role.capitalize()} Book Management",
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
                ft.FilledButton("Add New Books", icon=ft.Icons.LIBRARY_ADD_ROUNDED, on_click=self._open_add_books_dialog_handler, height=48)
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

    def _process_add_new_books_batch(self, db: Session, items_to_process: List[Dict[str, Any]], current_user: User) -> Tuple[int, int, List[str]]:
        """
        Callback for BookActionDialog to add new books.
        items_to_process contains dicts from TempBookActionItem.to_submission_dict()
        """
        books_for_service_call = []
        for item_data in items_to_process:
            books_for_service_call.append({
                "game_id": item_data['game_id'],
                "book_number_str": item_data['book_number_str'],
                "game_number_str": item_data['game_number_str'] # For error messages if any
            })

        created_books, service_errors = self.book_service.add_books_in_batch(db, books_for_service_call)

        success_count = len(created_books)
        failure_count = len(service_errors)

        return success_count, failure_count, service_errors


    def _open_add_books_dialog_handler(self, e: ft.ControlEvent):
        add_books_dialog = BookActionDialog(
            page_ref=self.page,
            current_user_ref=self.current_user, # Pass current user for the callback
            dialog_title="Add New Books to Inventory",
            action_button_text="Confirm & Add Books",
            action_type=BOOK_ACTION_ADD_NEW,
            on_confirm_batch_callback=self._process_add_new_books_batch,
            game_service=self.game_service,
            book_service=self.book_service,
            on_success_trigger_refresh=lambda: self.books_table_component.refresh_data_and_ui(self.search_bar.get_value()),
            require_ticket_scan=False # For adding books, ticket number is not scanned
        )
        add_books_dialog.open_dialog()