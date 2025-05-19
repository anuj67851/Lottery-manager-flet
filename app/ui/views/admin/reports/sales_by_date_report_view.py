import flet as ft
import datetime
from typing import List, Optional, Dict, Any

from app.constants import ADMIN_DASHBOARD_ROUTE
from app.core.models import User
from app.services import UserService, ReportService
from app.data.database import get_db_session
from app.data import crud_users
from app.ui.components.common.appbar_factory import create_appbar
from app.ui.components.common.paginated_data_table import PaginatedDataTable

class SalesByDateReportView(ft.Container):
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

        self.user_service = UserService()
        self.report_service = ReportService()

        self.all_users_for_filter: List[User] = []
        self._selected_user_id_filter: Optional[int] = None
        self._selected_start_date: Optional[datetime.date] = datetime.date.today() - datetime.timedelta(days=1)
        self._selected_end_date: Optional[datetime.date] = datetime.date.today()

        self.report_data_cache: List[Dict[str, Any]] = []

        self.file_picker = ft.FilePicker(on_result=self._on_file_picker_result)

        self.start_date_picker_ref = ft.DatePicker(
            on_change=lambda e: self._on_date_selected(e, 'start'),
            first_date=datetime.datetime(2020, 1, 1),
            last_date=datetime.datetime.now() + datetime.timedelta(days=365),
            help_text="Select Start Date"
        )
        self.end_date_picker_ref = ft.DatePicker(
            on_change=lambda e: self._on_date_selected(e, 'end'),
            first_date=datetime.datetime(2020, 1, 1),
            last_date=datetime.datetime.now() + datetime.timedelta(days=365),
            help_text="Select End Date"
        )

        if self.start_date_picker_ref not in self.page.overlay:
            self.page.overlay.append(self.start_date_picker_ref)
        if self.end_date_picker_ref not in self.page.overlay:
            self.page.overlay.append(self.end_date_picker_ref)
        if self.file_picker not in self.page.overlay:
            self.page.overlay.append(self.file_picker)


        self.start_date_button = ft.ElevatedButton(
            self._selected_start_date.strftime('%Y-%m-%d') if self._selected_start_date else "Start Date",
            icon=ft.Icons.CALENDAR_MONTH, on_click=lambda _: self._open_date_picker('start'),
            tooltip="Select report start date"
        )
        self.end_date_button = ft.ElevatedButton(
            self._selected_end_date.strftime('%Y-%m-%d') if self._selected_end_date else "End Date",
            icon=ft.Icons.CALENDAR_MONTH, on_click=lambda _: self._open_date_picker('end'),
            tooltip="Select report end date"
        )

        self.user_filter_dropdown = ft.Dropdown(
            label="Filter by User", hint_text="All Users",
            on_change=self._on_user_filter_change, width=250, border_radius=8,
            options=[ft.dropdown.Option(key="", text="All Users")]
        )
        self.generate_report_button = ft.FilledButton("Generate Report", icon=ft.Icons.SEARCH, on_click=self._generate_report_data_and_display, height=45)
        self.export_pdf_button = ft.FilledButton("Export to PDF", icon=ft.Icons.PICTURE_AS_PDF, on_click=self._export_report_to_pdf, height=45, disabled=True)

        self.error_text_widget = ft.Text(visible=False, color=ft.Colors.RED_700, weight=ft.FontWeight.BOLD)
        self.summary_total_sales_widget = ft.Text("Total Sales: $0.00", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD)
        self.summary_total_tickets_widget = ft.Text("Total Tickets: 0", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD)

        column_definitions: List[Dict[str, Any]] = [
            {"key": "date", "label": "Date/Time", "sortable": True,
             "display_formatter": lambda val, item: ft.Text(val.strftime("%Y-%m-%d %H:%M") if isinstance(val, datetime.datetime) else (val.strftime("%Y-%m-%d") if isinstance(val, datetime.date) else ""), size=12.5)},
            {"key": "username", "label": "User", "sortable": True, "searchable": True,
             "display_formatter": lambda val, item: ft.Text(str(val) if val is not None else "", size=12.5)},
            {"key": "game_name", "label": "Game", "sortable": True, "searchable": True,
             "display_formatter": lambda val, item: ft.Text(str(val) if val is not None else "", size=12.5)},
            {"key": "book_number", "label": "Book #", "sortable": True,
             "display_formatter": lambda val, item: ft.Text(str(val) if val is not None else "", size=12.5)},
            {"key": "ticket_order", "label": "Order", "sortable": False,
             "display_formatter": lambda val, item: ft.Text(str(val).capitalize() if val is not None else "", size=12.5)},
            {"key": "start_number", "label": "Start #", "sortable": False, "numeric": True,
             "display_formatter": lambda val, item: ft.Text(str(val) if val is not None else "", size=12.5)},
            {"key": "end_number", "label": "End #", "sortable": False, "numeric": True,
             "display_formatter": lambda val, item: ft.Text(str(val) if val is not None else "", size=12.5)},
            {"key": "count", "label": "Qty", "sortable": True, "numeric": True,
             "display_formatter": lambda val, item: ft.Text(str(val) if val is not None else "0", size=12.5, weight=ft.FontWeight.BOLD)},
            {"key": "game_price", "label": "Tkt Price", "sortable": False, "numeric": True,
             "display_formatter": lambda val, item: ft.Text(f"${val:.2f}" if val is not None else "$0.00", size=12.5)},
            {"key": "price", "label": "Total Value", "sortable": True, "numeric": True,
             "display_formatter": lambda val, item: ft.Text(f"${val:.2f}" if val is not None else "$0.00", size=12.5, weight=ft.FontWeight.BOLD)},
        ]

        self.report_table = PaginatedDataTable[Dict[str, Any]](
            page=self.page,
            fetch_all_data_func=lambda: self.report_data_cache,
            column_definitions=column_definitions,
            action_cell_builder=None,
            rows_per_page=15,
            initial_sort_key="date",
            initial_sort_ascending=False,
            no_data_message="No sales data found. Adjust filters and click 'Generate Report'.",
        )

        self.page.appbar = create_appbar(
            page=self.page, router=self.router, title_text=f"{self.current_user.role.capitalize()} > Sales by Date Report",
            current_user=self.current_user, license_status=self.license_status,
            leading_widget=ft.IconButton(ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED, tooltip="Go Back", icon_color=ft.Colors.WHITE, on_click=self._go_back)
        )
        self.content = self._build_body()
        self._load_initial_filters()

    def _go_back(self, e):
        nav_params = {**self.previous_view_params, "current_user": self.current_user, "license_status": self.license_status}
        self.router.navigate_to(self.previous_view_route, **nav_params)

    def _update_date_button_text(self, date_type: str):
        if date_type == 'start' and self._selected_start_date:
            self.start_date_button.text = self._selected_start_date.strftime('%Y-%m-%d')
            if self.start_date_button.page: self.start_date_button.update()
        elif date_type == 'end' and self._selected_end_date:
            self.end_date_button.text = self._selected_end_date.strftime('%Y-%m-%d')
            if self.end_date_button.page: self.end_date_button.update()

    def _on_date_selected(self, e: ft.ControlEvent, date_type: str):
        selected_datetime_val = e.control.value

        picker_to_close = self.start_date_picker_ref if date_type == 'start' else self.end_date_picker_ref
        picker_to_close.open = False

        if selected_datetime_val:
            if date_type == 'start':
                self._selected_start_date = selected_datetime_val.date()
            elif date_type == 'end':
                self._selected_end_date = selected_datetime_val.date()
            self._update_date_button_text(date_type)
            self._validate_dates()

        self.page.update()


    def _validate_dates(self):
        if self._selected_start_date and self._selected_end_date and self._selected_start_date > self._selected_end_date:
            self.error_text_widget.value = "Error: Start date cannot be after end date."
            self.error_text_widget.visible = True
        else:
            self.error_text_widget.value = ""
            self.error_text_widget.visible = False
        if self.error_text_widget.page: self.error_text_widget.update()


    def _open_date_picker(self, date_type: str):
        current_selection_date = self._selected_start_date if date_type == 'start' else self._selected_end_date
        initial_dt = datetime.datetime.combine(current_selection_date, datetime.time.min) if current_selection_date else datetime.datetime.now()

        picker_to_open = self.start_date_picker_ref if date_type == 'start' else self.end_date_picker_ref

        picker_to_open.current_date = initial_dt

        picker_to_open.open = True
        self.page.update()


    def _load_initial_filters(self):
        try:
            with get_db_session() as db:
                self.all_users_for_filter = self.user_service.get_all_users(db)

            options = [ft.dropdown.Option(key="", text="All Users")] # Key is empty string
            options.extend([ft.dropdown.Option(key=str(user.id), text=user.username) for user in self.all_users_for_filter])
            self.user_filter_dropdown.options = options
            self.user_filter_dropdown.value = "" # Set initial value to the key of "All Users"
            if self.user_filter_dropdown.page: self.user_filter_dropdown.update()
            self._update_date_button_text('start')
            self._update_date_button_text('end')

        except Exception as e:
            self.error_text_widget.value = f"Error loading filters: {e}"
            self.error_text_widget.visible = True
            if self.error_text_widget.page: self.error_text_widget.update()

    def _on_user_filter_change(self, e: ft.ControlEvent):
        selected_value = e.control.value # This should be the 'key' of the Dropdown.Option

        if selected_value == "":  # Key for "All Users"
            self._selected_user_id_filter = None
        elif selected_value is not None and isinstance(selected_value, str) and selected_value.isdigit():
            try:
                self._selected_user_id_filter = int(selected_value)
            except ValueError:
                # This should not happen if isdigit() is true, but as a safeguard
                print(f"Warning: Could not convert supposedly digit Dropdown key '{selected_value}' to int. Defaulting to 'All Users'.")
                self._selected_user_id_filter = None
        else:
            # This case means selected_value is something unexpected (e.g., None, or a non-digit string other than "")
            # It might even be the 'text' of an option if Flet's behavior is inconsistent or misconfigured.
            print(f"Warning: Unexpected Dropdown value/key for user filter: '{selected_value}' (type: {type(selected_value)}). Defaulting to 'All Users'.")
            self._selected_user_id_filter = None
            # If the actual text "All Users" is somehow passed as 'selected_value'
            if selected_value == "All Users":
                self._selected_user_id_filter = None # Explicitly handle this


    def _generate_report_data_and_display(self, e: ft.ControlEvent = None):
        self.error_text_widget.value = ""
        self.error_text_widget.visible = False
        self.export_pdf_button.disabled = True
        self.report_data_cache = []

        if not self._selected_start_date or not self._selected_end_date:
            self.error_text_widget.value = "Please select both start and end dates."
            self.error_text_widget.visible = True
        elif self._selected_start_date > self._selected_end_date:
            self.error_text_widget.value = "Start date cannot be after end date."
            self.error_text_widget.visible = True

        if self.error_text_widget.visible:
            if self.error_text_widget.page: self.error_text_widget.update()
            if self.export_pdf_button.page: self.export_pdf_button.update()
            self.report_table.refresh_data_and_ui()
            self._update_summary_totals()
            return

        start_datetime = datetime.datetime.combine(self._selected_start_date, datetime.time.min)
        end_datetime = datetime.datetime.combine(self._selected_end_date, datetime.time.max)

        try:
            with get_db_session() as db:
                self.report_data_cache = self.report_service.get_sales_report_data(
                    db, start_datetime, end_datetime, self._selected_user_id_filter
                )

            self.report_table.refresh_data_and_ui()
            self.export_pdf_button.disabled = not bool(self.report_data_cache)

        except Exception as ex:
            self.report_data_cache = []
            self.report_table.refresh_data_and_ui()
            self.error_text_widget.value = f"Error generating report: {ex}"
            self.error_text_widget.visible = True

        self._update_summary_totals()

        if self.error_text_widget.page: self.error_text_widget.update()
        if self.export_pdf_button.page: self.export_pdf_button.update()
        if self.page: self.page.update()

    def _update_summary_totals(self):
        total_sales = sum(item.get('price', 0) for item in self.report_data_cache)
        total_tickets = sum(item.get('count', 0) for item in self.report_data_cache)
        self.summary_total_sales_widget.value = f"Total Sales: ${total_sales:.2f}"
        self.summary_total_tickets_widget.value = f"Total Tickets: {total_tickets}"
        if self.summary_total_sales_widget.page: self.summary_total_sales_widget.update()
        if self.summary_total_tickets_widget.page: self.summary_total_tickets_widget.update()

    def _export_report_to_pdf(self, e: ft.ControlEvent):
        if not self.report_data_cache:
            self.page.open(ft.SnackBar(ft.Text("No data to export. Generate a report first."), open=True))
            return
        if not self._selected_start_date or not self._selected_end_date:
            self.page.open(ft.SnackBar(ft.Text("Date range not selected."), open=True, bgcolor=ft.Colors.ERROR))
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"SalesReport_{self._selected_start_date.strftime('%Y%m%d')}-{self._selected_end_date.strftime('%Y%m%d')}_{timestamp}.pdf"

        self.file_picker.save_file(
            dialog_title="Save Sales Report PDF",
            file_name=default_filename,
            allowed_extensions=["pdf"]
        )

    def _on_file_picker_result(self, e: ft.FilePickerResultEvent):
        if e.path:
            save_path = e.path
            start_datetime = datetime.datetime.combine(self._selected_start_date, datetime.time.min)
            end_datetime = datetime.datetime.combine(self._selected_end_date, datetime.time.max)

            user_filter_name_for_pdf = "All Users"
            if self._selected_user_id_filter:
                try:
                    with get_db_session() as db:
                        user = crud_users.get_user_by_id(db, self._selected_user_id_filter)
                        if user: user_filter_name_for_pdf = user.username
                except Exception: pass

            success, msg = self.report_service.generate_sales_report_pdf_from_data(
                report_data=self.report_data_cache,
                start_date=start_datetime,
                end_date=end_datetime,
                user_filter_name=user_filter_name_for_pdf,
                pdf_save_path=save_path
            )
            if success:
                self.page.open(ft.SnackBar(ft.Text(f"Report saved to: {msg}"), open=True, bgcolor=ft.Colors.GREEN))
            else:
                self.page.open(ft.SnackBar(ft.Text(f"Error saving PDF: {msg}"), open=True, bgcolor=ft.Colors.ERROR))
        elif e.error:
            self.page.open(ft.SnackBar(ft.Text(f"File picker error: {e.error}"), open=True, bgcolor=ft.Colors.ERROR))

    def _build_body(self) -> ft.Container:
        filter_controls = [
            ft.Text("Date Range : ", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD),
            self.start_date_button,
            self.end_date_button,
            ft.Container(width=20),
            self.user_filter_dropdown,
            ft.Container(width=10),
            self.generate_report_button,
            ft.Container(width=5),
            self.export_pdf_button,
        ]

        filters_row = ft.Row(
            filter_controls,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10, wrap=True
        )

        summary_row = ft.Row(
            [self.summary_total_tickets_widget, ft.Container(width=20), self.summary_total_sales_widget],
            alignment=ft.MainAxisAlignment.END, spacing=20
        )

        report_card_content = ft.Column(
            [
                ft.Text("Sales Report Filters", style=ft.TextThemeStyle.TITLE_LARGE, weight=ft.FontWeight.BOLD),
                filters_row,
                self.error_text_widget,
                ft.Divider(height=15),
                ft.Text("Report Results", style=ft.TextThemeStyle.TITLE_LARGE, weight=ft.FontWeight.BOLD),
                self.report_table,
                ft.Divider(height=10),
                summary_row,
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