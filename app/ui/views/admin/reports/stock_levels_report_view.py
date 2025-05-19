import flet as ft
import datetime
from typing import List, Optional, Dict, Any

from app.constants import ADMIN_DASHBOARD_ROUTE
from app.core.models import User, Game as GameModel
from app.services import ReportService
from app.data.database import get_db_session
from app.ui.components.common.appbar_factory import create_appbar
from app.ui.components.common.paginated_data_table import PaginatedDataTable

class StockLevelsReportView(ft.Container):
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

        self.report_service = ReportService()
        self.all_games_for_filter: List[GameModel] = []
        self._selected_game_id_filter: Optional[int] = None
        self.report_data_cache: List[Dict[str, Any]] = []

        self.file_picker = ft.FilePicker(on_result=self._on_file_picker_result)
        if self.file_picker not in self.page.overlay:
            self.page.overlay.append(self.file_picker)

        self.game_filter_dropdown = ft.Dropdown(
            label="Filter by Game", hint_text="All Active Games",
            on_change=self._on_game_filter_change, width=300, border_radius=8,
            options=[ft.dropdown.Option(key="", text="All Active Games")]
        )
        self.generate_report_button = ft.FilledButton("Generate Report", icon=ft.Icons.SEARCH, on_click=self._generate_report_data_and_display, height=45)
        self.export_pdf_button = ft.FilledButton("Export to PDF", icon=ft.Icons.PICTURE_AS_PDF, on_click=self._export_report_to_pdf, height=45, disabled=True)
        self.error_text_widget = ft.Text(visible=False, color=ft.Colors.RED_700, weight=ft.FontWeight.BOLD)

        self.summary_total_active_stock_value = ft.Text("Total Active Stock Value: $0.00", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD)

        column_definitions: List[Dict[str, Any]] = [
            {"key": "game_name", "label": "Game Name", "sortable": True, "searchable": True, "display_formatter": lambda val, item: ft.Text(str(val), size=12.5)},
            {"key": "game_number", "label": "Game No.", "sortable": True, "numeric": True, "searchable": True, "display_formatter": lambda val, item: ft.Text(str(val), size=12.5)},
            {"key": "game_price_per_ticket", "label": "Tkt Price", "sortable": False, "numeric": True, "display_formatter": lambda val, item: ft.Text(f"${val:.2f}" if val is not None else "", size=12.5)},
            {"key": "total_books", "label": "Total Bks", "sortable": True, "numeric": True, "display_formatter": lambda val, item: ft.Text(str(val), size=12.5)},
            {"key": "active_books", "label": "Active Bks", "sortable": True, "numeric": True, "display_formatter": lambda val, item: ft.Text(str(val), color=ft.Colors.GREEN_700, weight=ft.FontWeight.BOLD, size=12.5)},
            {"key": "finished_books", "label": "Finished Bks", "sortable": True, "numeric": True, "display_formatter": lambda val, item: ft.Text(str(val), color=ft.Colors.BLUE_GREY_400, size=12.5)},
            {"key": "pending_books", "label": "Pending Bks", "sortable": True, "numeric": True, "display_formatter": lambda val, item: ft.Text(str(val), color=ft.Colors.ORANGE_ACCENT_700, size=12.5)},
            {"key": "active_stock_value", "label": "Active Stock Val", "sortable": True, "numeric": True, "display_formatter": lambda val, item: ft.Text(f"${val:.2f}" if val is not None else "$0.00", weight=ft.FontWeight.BOLD, size=12.5)},
        ]
        self.report_table = PaginatedDataTable[Dict[str, Any]](
            page=self.page, fetch_all_data_func=lambda: self.report_data_cache,
            column_definitions=column_definitions, action_cell_builder=None,
            rows_per_page=15, initial_sort_key="game_name", initial_sort_ascending=True,
            no_data_message="No stock data found. Adjust filter and click 'Generate Report'."
        )
        self.page.appbar = create_appbar(
            page=self.page, router=self.router, title_text=f"{self.current_user.role.capitalize()} > Stock Levels Report",
            current_user=self.current_user, license_status=self.license_status,
            leading_widget=ft.IconButton(ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED, tooltip="Go Back", icon_color=ft.Colors.WHITE, on_click=self._go_back)
        )
        self.content = self._build_body()
        self._load_initial_filters()
        self._generate_report_data_and_display() # Auto-generate on load

    def _go_back(self, e):
        nav_params = {**self.previous_view_params, "current_user": self.current_user, "license_status": self.license_status}
        self.router.navigate_to(self.previous_view_route, **nav_params)

    def _load_initial_filters(self):
        try:
            with get_db_session() as db:
                self.all_games_for_filter = self.report_service.get_all_games_for_filter(db) # Gets all games
            options = [ft.dropdown.Option(key="", text="All Active Games")] # Default filter text
            # Filter dropdown to show only active games for selection
            options.extend([ft.dropdown.Option(key=str(game.id), text=f"{game.game_number} - {game.name}") for game in self.all_games_for_filter if not game.is_expired])
            self.game_filter_dropdown.options = options
            self.game_filter_dropdown.value = ""
            if self.game_filter_dropdown.page: self.game_filter_dropdown.update()
        except Exception as e: self._show_error(f"Error loading game filters: {e}")

    def _on_game_filter_change(self, e: ft.ControlEvent):
        self._selected_game_id_filter = int(e.control.value) if e.control.value and e.control.value.isdigit() else None

    def _generate_report_data_and_display(self, e: ft.ControlEvent = None):
        self._clear_error()
        self.export_pdf_button.disabled = True
        self.report_data_cache = []
        try:
            with get_db_session() as db:
                self.report_data_cache = self.report_service.get_stock_levels_report_data(db, self._selected_game_id_filter)
            self.report_table.refresh_data_and_ui()
            self.export_pdf_button.disabled = not bool(self.report_data_cache)
        except Exception as ex:
            self._show_error(f"Error generating report: {ex}")
        self._update_summary_totals()
        if self.export_pdf_button.page: self.export_pdf_button.update()
        if self.page: self.page.update()

    def _update_summary_totals(self):
        total_value = sum(item.get('active_stock_value', 0) for item in self.report_data_cache)
        self.summary_total_active_stock_value.value = f"Total Active Stock Value: ${total_value:.2f}"
        if self.summary_total_active_stock_value.page: self.summary_total_active_stock_value.update()

    def _export_report_to_pdf(self, e: ft.ControlEvent):
        if not self.report_data_cache:
            self.page.open(ft.SnackBar(ft.Text("No data to export."), open=True)); return

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        game_filter_name_suffix = "AllActiveGames"
        game_filter_display_name = "All Active Games"
        if self._selected_game_id_filter:
            selected_game = next((g for g in self.all_games_for_filter if g.id == self._selected_game_id_filter), None)
            if selected_game:
                game_filter_name_suffix = f"Game{selected_game.game_number}"
                game_filter_display_name = f"{selected_game.game_number} - {selected_game.name}"

        default_filename = f"StockLevelsReport_{game_filter_name_suffix}_{timestamp}.pdf"
        self.file_picker.save_file(dialog_title="Save Stock Levels Report PDF", file_name=default_filename, allowed_extensions=["pdf"])

    def _on_file_picker_result(self, e: ft.FilePickerResultEvent):
        if e.path:
            game_filter_display_name = "All Active Games" # Default for PDF title
            if self._selected_game_id_filter:
                selected_game = next((g for g in self.all_games_for_filter if g.id == self._selected_game_id_filter), None)
                if selected_game: game_filter_display_name = f"{selected_game.game_number} - {selected_game.name}"

            success, msg = self.report_service.generate_stock_levels_report_pdf(self.report_data_cache, game_filter_display_name, e.path)
            if success: self.page.open(ft.SnackBar(ft.Text(f"Report saved to: {msg}"), open=True, bgcolor=ft.Colors.GREEN))
            else: self.page.open(ft.SnackBar(ft.Text(f"Error saving PDF: {msg}"), open=True, bgcolor=ft.Colors.ERROR))
        elif e.error: self.page.open(ft.SnackBar(ft.Text(f"File picker error: {e.error}"), open=True, bgcolor=ft.Colors.ERROR))

    def _show_error(self, message: str):
        self.error_text_widget.value = message; self.error_text_widget.visible = True
        if self.error_text_widget.page: self.error_text_widget.update()
    def _clear_error(self):
        self.error_text_widget.value = ""; self.error_text_widget.visible = False
        if self.error_text_widget.page: self.error_text_widget.update()

    def _build_body(self) -> ft.Container:
        filters_row = ft.Row(
            [self.game_filter_dropdown, self.generate_report_button, self.export_pdf_button],
            alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=10
        )
        summary_row = ft.Row([self.summary_total_active_stock_value], alignment=ft.MainAxisAlignment.END)
        report_card_content = ft.Column(
            [
                ft.Text("Stock Levels Report Filters", style=ft.TextThemeStyle.TITLE_LARGE, weight=ft.FontWeight.BOLD),
                filters_row, self.error_text_widget, ft.Divider(height=15),
                ft.Text("Report Results", style=ft.TextThemeStyle.TITLE_LARGE, weight=ft.FontWeight.BOLD),
                self.report_table, ft.Divider(height=10), summary_row,
            ],
            spacing=15, expand=True, scroll=ft.ScrollMode.ADAPTIVE,
        )
        TARGET_CARD_MAX_WIDTH = 1100
        page_width_for_calc = self.page.width if self.page.width and self.page.width > 0 else TARGET_CARD_MAX_WIDTH + 40
        card_effective_width = min(TARGET_CARD_MAX_WIDTH, page_width_for_calc - 40)
        card_effective_width = max(card_effective_width, 800)
        report_card = ft.Card(
            content=ft.Container(content=report_card_content, padding=20, border_radius=ft.border_radius.all(10)),
            elevation=2, width=card_effective_width
        )
        return ft.Container(content=report_card, alignment=ft.alignment.top_center, padding=20, expand=True)