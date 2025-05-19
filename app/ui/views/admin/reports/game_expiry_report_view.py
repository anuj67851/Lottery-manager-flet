import flet as ft
import datetime
from typing import List, Optional, Dict, Any

from app.constants import ADMIN_DASHBOARD_ROUTE
from app.core.models import User
from app.services import ReportService
from app.data.database import get_db_session
from app.ui.components.common.appbar_factory import create_appbar
from app.ui.components.common.paginated_data_table import PaginatedDataTable

class GameExpiryReportView(ft.Container):
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
        self._selected_status_filter: Optional[str] = None # "active" or "expired"
        self._selected_expired_start_date: Optional[datetime.date] = None
        self._selected_expired_end_date: Optional[datetime.date] = None
        self.report_data_cache: List[Dict[str, Any]] = []

        self.file_picker = ft.FilePicker(on_result=self._on_file_picker_result)
        self.expired_start_date_picker = ft.DatePicker(on_change=lambda e: self._on_date_selected(e, 'start'), help_text="Expired Start Date")
        self.expired_end_date_picker = ft.DatePicker(on_change=lambda e: self._on_date_selected(e, 'end'), help_text="Expired End Date")

        # Add pickers to page overlay if not already present
        for picker in [self.file_picker, self.expired_start_date_picker, self.expired_end_date_picker]:
            if picker not in self.page.overlay:
                self.page.overlay.append(picker)

        self.status_filter_dropdown = ft.Dropdown(
            label="Filter by Status", hint_text="All Statuses",
            on_change=self._on_status_filter_change, width=200, border_radius=8,
            options=[
                ft.dropdown.Option(key="", text="All Statuses"),
                ft.dropdown.Option(key="active", text="Active"),
                ft.dropdown.Option(key="expired", text="Expired"),
            ]
        )
        self.expired_start_date_button = ft.ElevatedButton("Expired Start", icon=ft.Icons.CALENDAR_MONTH, on_click=lambda _: self._open_date_picker('start'), disabled=True)
        self.expired_end_date_button = ft.ElevatedButton("Expired End", icon=ft.Icons.CALENDAR_MONTH, on_click=lambda _: self._open_date_picker('end'), disabled=True)
        self.generate_report_button = ft.FilledButton("Generate Report", icon=ft.Icons.SEARCH, on_click=self._generate_report_data_and_display, height=45)
        self.export_pdf_button = ft.FilledButton("Export to PDF", icon=ft.Icons.PICTURE_AS_PDF, on_click=self._export_report_to_pdf, height=45, disabled=True)
        self.error_text_widget = ft.Text(visible=False, color=ft.Colors.RED_700, weight=ft.FontWeight.BOLD)

        column_definitions: List[Dict[str, Any]] = [
            {"key": "name", "label": "Game Name", "sortable": True, "searchable": True, "display_formatter": lambda val, item: ft.Text(str(val), size=12.5)},
            {"key": "game_number", "label": "Game No.", "sortable": True, "numeric": True, "searchable": True, "display_formatter": lambda val, item: ft.Text(str(val), size=12.5)},
            {"key": "price", "label": "Price", "sortable": True, "numeric": True, "display_formatter": lambda val, item: ft.Text(f"${val:.2f}" if val is not None else "", size=12.5)},
            {"key": "total_tickets", "label": "Total Tkts", "sortable": True, "numeric": True, "display_formatter": lambda val, item: ft.Text(str(val), size=12.5)},
            {"key": "is_expired", "label": "Status", "sortable": True, "display_formatter": lambda val, item: ft.Text("Expired" if val else "Active", color=ft.Colors.RED if val else ft.Colors.GREEN, weight=ft.FontWeight.BOLD, size=12.5)},
            {"key": "created_date", "label": "Created On", "sortable": True, "display_formatter": lambda val, item: ft.Text(val.strftime("%Y-%m-%d") if val else "", size=12.5)},
            {"key": "expired_date", "label": "Expired On", "sortable": True, "display_formatter": lambda val, item: ft.Text(val.strftime("%Y-%m-%d") if val else "", size=12.5)},
        ]
        self.report_table = PaginatedDataTable[Dict[str, Any]](
            page=self.page, fetch_all_data_func=lambda: self.report_data_cache,
            column_definitions=column_definitions, action_cell_builder=None,
            rows_per_page=15, initial_sort_key="is_expired", initial_sort_ascending=False, # Show expired first
            no_data_message="No games found. Adjust filters and click 'Generate Report'."
        )
        self.page.appbar = create_appbar(
            page=self.page, router=self.router, title_text=f"{self.current_user.role.capitalize()} > Game Expiry Report",
            current_user=self.current_user, license_status=self.license_status,
            leading_widget=ft.IconButton(ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED, tooltip="Go Back", icon_color=ft.Colors.WHITE, on_click=self._go_back)
        )
        self.content = self._build_body()
        self._generate_report_data_and_display() # Auto-generate on load

    def _go_back(self, e):
        nav_params = {**self.previous_view_params, "current_user": self.current_user, "license_status": self.license_status}
        self.router.navigate_to(self.previous_view_route, **nav_params)

    def _on_status_filter_change(self, e: ft.ControlEvent):
        self._selected_status_filter = e.control.value if e.control.value else None
        is_expired_selected = self._selected_status_filter == "expired"
        self.expired_start_date_button.disabled = not is_expired_selected
        self.expired_end_date_button.disabled = not is_expired_selected
        if not is_expired_selected:
            self._selected_expired_start_date = None
            self._selected_expired_end_date = None
            self.expired_start_date_button.text = "Expired Start"
            self.expired_end_date_button.text = "Expired End"
        if self.expired_start_date_button.page: self.expired_start_date_button.update()
        if self.expired_end_date_button.page: self.expired_end_date_button.update()

    def _on_date_selected(self, e: ft.ControlEvent, date_type: str):
        picker = self.expired_start_date_picker if date_type == 'start' else self.expired_end_date_picker
        button = self.expired_start_date_button if date_type == 'start' else self.expired_end_date_button
        selected_dt = e.control.value
        picker.open = False # Close picker
        if selected_dt:
            if date_type == 'start': self._selected_expired_start_date = selected_dt.date()
            else: self._selected_expired_end_date = selected_dt.date()
            button.text = selected_dt.strftime('%Y-%m-%d')
        else: # Date cleared
            if date_type == 'start': self._selected_expired_start_date = None; button.text = "Expired Start"
            else: self._selected_expired_end_date = None; button.text = "Expired End"
        if button.page: button.update()
        self._validate_dates()
        if self.page: self.page.update()

    def _validate_dates(self):
        if self._selected_expired_start_date and self._selected_expired_end_date and self._selected_expired_start_date > self._selected_expired_end_date:
            self._show_error("Error: Expired start date cannot be after end date.")
        else: self._clear_error()

    def _open_date_picker(self, date_type: str):
        picker = self.expired_start_date_picker if date_type == 'start' else self.expired_end_date_picker
        current_date_val = self._selected_expired_start_date if date_type == 'start' else self._selected_expired_end_date
        picker.current_date = datetime.datetime.combine(current_date_val, datetime.time.min) if current_date_val else datetime.datetime.now()
        picker.open = True
        self.page.update()

    def _generate_report_data_and_display(self, e: ft.ControlEvent = None):
        self._clear_error()
        self._validate_dates()
        if self.error_text_widget.visible:
            if self.page: self.page.update(); return

        self.export_pdf_button.disabled = True
        self.report_data_cache = []
        start_dt = datetime.datetime.combine(self._selected_expired_start_date, datetime.time.min) if self._selected_expired_start_date else None
        end_dt = datetime.datetime.combine(self._selected_expired_end_date, datetime.time.max) if self._selected_expired_end_date else None
        try:
            with get_db_session() as db:
                self.report_data_cache = self.report_service.get_game_expiry_report_data(db, self._selected_status_filter, start_dt, end_dt)
            self.report_table.refresh_data_and_ui()
            self.export_pdf_button.disabled = not bool(self.report_data_cache)
        except Exception as ex:
            self._show_error(f"Error generating report: {ex}")
        if self.export_pdf_button.page: self.export_pdf_button.update()
        if self.page: self.page.update()

    def _export_report_to_pdf(self, e: ft.ControlEvent):
        if not self.report_data_cache:
            self.page.open(ft.SnackBar(ft.Text("No data to export."), open=True)); return

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        status_suffix = self._selected_status_filter if self._selected_status_filter else "AllStatuses"
        default_filename = f"GameExpiryReport_{status_suffix}_{timestamp}.pdf"
        self.file_picker.save_file(dialog_title="Save Game Expiry Report PDF", file_name=default_filename, allowed_extensions=["pdf"])

    def _on_file_picker_result(self, e: ft.FilePickerResultEvent):
        if e.path:
            filter_text = f"Status: {self._selected_status_filter.capitalize() if self._selected_status_filter else 'All'}"
            if self._selected_status_filter == "expired":
                if self._selected_expired_start_date: filter_text += f" | Expired From: {self._selected_expired_start_date.strftime('%Y-%m-%d')}"
                if self._selected_expired_end_date: filter_text += f" | Expired To: {self._selected_expired_end_date.strftime('%Y-%m-%d')}"

            success, msg = self.report_service.generate_game_expiry_report_pdf(self.report_data_cache, filter_text, e.path)
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
        date_filter_row = ft.Row([self.expired_start_date_button, self.expired_end_date_button], spacing=10, visible= (self._selected_status_filter == "expired"))
        self.expired_start_date_button.visible = self.expired_end_date_button.visible = (self._selected_status_filter == "expired")

        filters_row = ft.Row(
            [self.status_filter_dropdown, self.expired_start_date_button, self.expired_end_date_button,
             self.generate_report_button, self.export_pdf_button],
            alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=10, wrap=True
        )
        report_card_content = ft.Column(
            [
                ft.Text("Game Expiry Report Filters", style=ft.TextThemeStyle.TITLE_LARGE, weight=ft.FontWeight.BOLD),
                filters_row, self.error_text_widget, ft.Divider(height=15),
                ft.Text("Report Results", style=ft.TextThemeStyle.TITLE_LARGE, weight=ft.FontWeight.BOLD),
                self.report_table,
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