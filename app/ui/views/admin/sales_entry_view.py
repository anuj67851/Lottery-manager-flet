import flet as ft
import datetime
from typing import List, Optional, Dict, Any

from app.constants import ADMIN_DASHBOARD_ROUTE, MIN_REQUIRED_SCAN_LENGTH_WITH_TICKET
from app.core.models import User, ShiftSubmission # Added ShiftSubmission for type hint
from app.services import SalesEntryService, ShiftService
from app.data.database import get_db_session
from app.core.exceptions import ValidationError, DatabaseError, GameNotFoundError, BookNotFoundError

from app.ui.components.common.appbar_factory import create_appbar
from app.ui.components.common.dialog_factory import create_confirmation_dialog
from app.ui.components.tables.sales_entry_items_table import SalesEntryItemsTable # Ensure this is the correct path
from app.ui.components.tables.sales_entry_item_data import SalesEntryItemData # Ensure this is the correct path
from app.ui.components.common.scan_input_handler import ScanInputHandler
from app.ui.components.widgets import NumberDecimalField


class SalesEntryView(ft.Container):
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

        self.sales_entry_service = SalesEntryService()
        self.shift_service = ShiftService()

        self.reported_online_sales_field = NumberDecimalField(
            label="Total Online Sales ($)", is_money_field=True, currency_symbol="$",
            hint_text="Cumulative from terminal", expand=True, height=50, border_radius=8, is_integer_only=False )
        self.reported_online_payouts_field = NumberDecimalField(
            label="Total Online Payouts ($)", is_money_field=True, currency_symbol="$",
            hint_text="Cumulative from terminal", expand=True, height=50, border_radius=8, is_integer_only=False )
        self.reported_instant_payouts_field = NumberDecimalField(
            label="Total Instant Payouts ($)", is_money_field=True, currency_symbol="$",
            hint_text="Cumulative from terminal", expand=True, height=50, border_radius=8, is_integer_only=True )
        self.actual_cash_in_drawer_field = NumberDecimalField(
            label="Lottery Cash in Drawer ($)", is_money_field=True, currency_symbol="$",
            hint_text="Lottery cash in drawer report", expand=True, height=50, border_radius=8, is_integer_only=False )

        self.today_date_widget = ft.Text(
            f"Date: {datetime.datetime.now().strftime('%A, %B %d, %Y %I:%M %p')}",
            style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD )
        self.books_in_table_count_widget = ft.Text(
            "Books In Table: 0", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.NORMAL )
        self.pending_entry_books_count_widget = ft.Text(
            "Pending Entry: 0", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.NORMAL, color=ft.Colors.ORANGE_ACCENT_700 )
        self.scanner_text_field: ft.TextField = ft.TextField(
            label="Scan Full Book Code (Game+Book+Ticket)",
            hint_text=f"Input {MIN_REQUIRED_SCAN_LENGTH_WITH_TICKET} chars total.",
            autofocus=True, border_radius=8, prefix_icon=ft.Icons.QR_CODE_SCANNER_ROUNDED,
            expand=True, height=50 )
        self.scan_input_handler: Optional[ScanInputHandler] = None
        self.sales_items_table_component: Optional[SalesEntryItemsTable] = None
        self.grand_total_sales_widget = ft.Text("Grand Total Instant Sales: $0.00", weight=ft.FontWeight.BOLD, size=16)
        self.total_tickets_sold_widget = ft.Text("Total Instant Tickets Sold: 0", weight=ft.FontWeight.BOLD, size=16)
        self.scan_error_text_widget = ft.Text("", color=ft.Colors.RED_ACCENT_700, visible=False, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)

        self.page.appbar = create_appbar(
            page=self.page, router=self.router, title_text=f"{self.current_user.role.capitalize()} > Sales Entry & Shift Submission",
            current_user=self.current_user, license_status=self.license_status,
            leading_widget=ft.IconButton(
                icon=ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED, tooltip="Go Back",
                icon_color=ft.Colors.WHITE, on_click=self._go_back ))

        self.content = self._build_body()
        self._load_initial_data_for_table()

    def _go_back(self, e):
        nav_params = {**self.previous_view_params}
        if "current_user" not in nav_params and self.current_user: nav_params["current_user"] = self.current_user
        if "license_status" not in nav_params and self.license_status is not None: nav_params["license_status"] = self.license_status
        self.router.navigate_to(self.previous_view_route, **nav_params)

    def _load_initial_data_for_table(self):
        if self.sales_items_table_component:
            self.sales_items_table_component.load_initial_active_books()
        for field in [self.reported_online_sales_field, self.reported_online_payouts_field, self.reported_instant_payouts_field, self.actual_cash_in_drawer_field]:
            field.value = None
            field.error_text = None
            field.last_valid_value = ""
            if field.page: field.update()
        self._clear_scan_error_properties()
        if self.scan_input_handler and self.scan_input_handler.scan_text_field:
            self.scan_input_handler.scan_text_field.value = ""
            if self.scan_input_handler.scan_text_field.page: self.scan_input_handler.scan_text_field.update()
        self._update_totals_and_book_counts_properties()
        if self.page: self.page.update()


    def _clear_scan_error_properties(self):
        if self.scan_error_text_widget.visible:
            self.scan_error_text_widget.value = ""
            self.scan_error_text_widget.visible = False
            if self.scan_error_text_widget.page: self.scan_error_text_widget.update()


    def _handle_table_items_loaded(self, all_items: List[SalesEntryItemData]):
        self._update_totals_and_book_counts_properties()
        if self.page and self.page.controls:
            self.page.update()

    def _update_totals_and_book_counts_properties(self, changed_item_data: Optional[SalesEntryItemData] = None):
        if not self.sales_items_table_component: return
        all_display_items = self.sales_items_table_component.get_all_data_items()

        grand_total_instant_sales_val = sum(item.amount_calculated for item in all_display_items if item.is_processed_for_sale or item.all_tickets_sold_confirmed)
        total_instant_tickets_sold_val = sum(item.tickets_sold_calculated for item in all_display_items if item.is_processed_for_sale or item.all_tickets_sold_confirmed)

        pending_entry_count = sum(1 for item in all_display_items if not item.ui_new_ticket_no_str.strip() and not item.all_tickets_sold_confirmed)

        self.grand_total_sales_widget.value = f"Grand Total Instant Sales: ${grand_total_instant_sales_val:.2f}"
        self.total_tickets_sold_widget.value = f"Total Instant Tickets Sold: {total_instant_tickets_sold_val}"
        self.books_in_table_count_widget.value = f"Books In Table: {len(all_display_items)}"
        self.pending_entry_books_count_widget.value = f"Pending Entry: {pending_entry_count}"

        for widget in [self.grand_total_sales_widget, self.total_tickets_sold_widget, self.books_in_table_count_widget, self.pending_entry_books_count_widget]:
            if widget.page:
                widget.update()


    def _on_scan_complete_callback(self, parsed_data: Dict[str, str]):
        self._clear_scan_error_properties()
        game_no_str = parsed_data.get('game_no', '')
        book_no_str = parsed_data.get('book_no', '')
        ticket_no_str = parsed_data.get('ticket_no', '')
        self._process_scan_and_update_table(game_no_str, book_no_str, ticket_no_str)

    def _on_scan_error_callback(self, error_message: str):
        self.scan_error_text_widget.value = error_message
        self.scan_error_text_widget.visible = True
        if self.scan_error_text_widget.page: self.scan_error_text_widget.update()
        if self.scan_input_handler: self.scan_input_handler.focus_input()

    def _process_scan_and_update_table(self, game_no_str: str, book_no_str: str, ticket_no_str: str):
        self._clear_scan_error_properties()
        try:
            with get_db_session() as db:
                book_model_instance = self.sales_entry_service.get_or_create_book_for_sale(db, game_no_str, book_no_str)
            if self.sales_items_table_component:
                self.sales_items_table_component.add_or_update_book_for_sale(book_model_instance, ticket_no_str)
            else:
                raise Exception("Sales items table component not initialized.")
        except (ValidationError, GameNotFoundError, BookNotFoundError, DatabaseError) as e:
            self._on_scan_error_callback(str(e.message if hasattr(e, 'message') else e))
        except Exception as ex_general:
            self._on_scan_error_callback(f"Error processing scan: {type(ex_general).__name__} - {ex_general}")

        if self.scan_input_handler: self.scan_input_handler.focus_input()
        if self.page: self.page.update()


    def _handle_submit_shift_sales_click(self, e):
        if not self.sales_items_table_component:
            self.page.open(ft.SnackBar(ft.Text("Sales table not ready."), open=True, bgcolor=ft.Colors.ERROR)); return

        try:
            reported_online_sales_float = self.reported_online_sales_field.get_value_as_float()
            if reported_online_sales_float is None or reported_online_sales_float < 0: raise ValidationError("Reported Online Sales must be a non-negative number.")

            reported_online_payouts_float = self.reported_online_payouts_field.get_value_as_float()
            if reported_online_payouts_float is None or reported_online_payouts_float < 0: raise ValidationError("Reported Online Payouts must be a non-negative number.")

            reported_instant_payouts_float = self.reported_instant_payouts_field.get_value_as_float()
            if reported_instant_payouts_float is None or reported_instant_payouts_float < 0: raise ValidationError("Reported Instant Payouts must be a non-negative number.")

            actual_cash_in_drawer_float = self.actual_cash_in_drawer_field.get_value_as_float()
            if actual_cash_in_drawer_float is None or actual_cash_in_drawer_float < 0: raise ValidationError("Actual Cash in Drawer must be a non-negative number.")

        except ValidationError as ve:
            self._on_scan_error_callback(f"Input Error: {ve.message}"); return
        except Exception as ex_val:
            self._on_scan_error_callback(f"Input Error: Invalid number in reported totals - {ex_val}"); return

        self._clear_scan_error_properties()

        instant_sales_items_data_for_submission = [item.get_data_for_submission() for item in self.sales_items_table_component.get_all_items_for_submission()]
        all_current_table_items = self.sales_items_table_component.get_all_data_items()
        items_with_empty_fields: List[SalesEntryItemData] = []
        for item_data in all_current_table_items:
            if not item_data.ui_new_ticket_no_str.strip() and not item_data.all_tickets_sold_confirmed:
                is_already_for_submission = any(sub_item["book_db_id"] == item_data.book_db_id for sub_item in instant_sales_items_data_for_submission)
                if not is_already_for_submission: items_with_empty_fields.append(item_data)

        if items_with_empty_fields:
            self._prompt_for_empty_field_books_confirmation(
                items_with_empty_fields,
                reported_online_sales_float, reported_online_payouts_float,
                reported_instant_payouts_float, actual_cash_in_drawer_float,
                instant_sales_items_data_for_submission )
        else:
            self._open_confirm_shift_submission_dialog(
                reported_online_sales_float, reported_online_payouts_float,
                reported_instant_payouts_float, actual_cash_in_drawer_float,
                instant_sales_items_data_for_submission )

    def _prompt_for_empty_field_books_confirmation(
            self, items_to_confirm: List[SalesEntryItemData],
            reported_online_sales_float: float, reported_online_payouts_float: float,
            reported_instant_payouts_float: float, actual_cash_in_drawer_float: float,
            current_sales_item_details: List[Dict[str, Any]]):
        book_details_str = "\n".join([f"- Game {item.book_model.game.game_number} / Book {item.book_number}" for item in items_to_confirm])
        dialog_content_column = ft.Column(
            [ ft.Text("The following books have no new ticket number entered:", weight=ft.FontWeight.BOLD),
              ft.Container(ft.Column(controls=[ft.Text(book_details_str, selectable=True)], scroll=ft.ScrollMode.ADAPTIVE), height=min(150, len(items_to_confirm)*26 + 20), padding=5),
              ft.Divider(height=10), ft.Text("Do you want to mark them as ALL TICKETS SOLD?"),
              ft.Text("Choosing 'No' will skip these specific books from this submission.", size=11, italic=True, color=ft.Colors.OUTLINE)
              ], tight=True, spacing=10, width=450 )
        def _handle_dialog_choice(mark_as_all_sold: bool):
            self.page.close(self.page.dialog)
            updated_sales_item_details = list(current_sales_item_details)
            if mark_as_all_sold:
                for item_data in items_to_confirm:
                    item_data.confirm_all_sold()
                    if self.sales_items_table_component:
                        self.sales_items_table_component.update_datarow_for_item(item_data.unique_id)
                    updated_sales_item_details.append(item_data.get_data_for_submission())
            self._update_totals_and_book_counts_properties()
            self._open_confirm_shift_submission_dialog(
                reported_online_sales_float, reported_online_payouts_float,
                reported_instant_payouts_float, actual_cash_in_drawer_float,
                updated_sales_item_details )
            if self.page: self.page.update()
        confirm_dialog = ft.AlertDialog(
            modal=True, title=ft.Text("Confirm Unentered Instant Sale Books"), content=dialog_content_column,
            actions=[ ft.TextButton("Cancel Submission", on_click=lambda _: self.page.close(self.page.dialog)),
                      ft.TextButton("No, Skip These Empty", on_click=lambda _: _handle_dialog_choice(False)),
                      ft.FilledButton("Yes, Mark All Sold", on_click=lambda _: _handle_dialog_choice(True)),
                      ], actions_alignment=ft.MainAxisAlignment.END, )
        self.page.dialog = confirm_dialog
        self.page.open(confirm_dialog)

    def _open_confirm_shift_submission_dialog(
            self, reported_online_sales_float: float, reported_online_payouts_float: float,
            reported_instant_payouts_float: float, actual_cash_in_drawer_float: float,
            sales_item_details: List[Dict[str, Any]]):
        total_instant_tickets = sum(item.get('tickets_sold_calculated', 0) for item in sales_item_details)
        total_instant_value_dollars = sum(item.get('amount_calculated', 0) for item in sales_item_details)

        confirmation_content_column = ft.Column([
            ft.Text("Please confirm the values you are submitting:", weight=ft.FontWeight.BOLD), ft.Divider(),
            ft.Text(f"Reported Total Online Sales Today: ${reported_online_sales_float:.2f}"),
            ft.Text(f"Reported Total Online Payouts Today: ${reported_online_payouts_float:.2f}"),
            ft.Text(f"Reported Total Instant Payouts Today: ${reported_instant_payouts_float:.2f}"),
            ft.Text(f"Actual Cash in Drawer: ${actual_cash_in_drawer_float:.2f}", weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Text("Instant Game Sales for this submission (from table):"),
            ft.Text(f"  Total Instant Tickets: {total_instant_tickets}"),
            ft.Text(f"  Total Instant Value: ${total_instant_value_dollars:.2f}"),
            ft.Divider(),
            ft.Text("This will finalize this set of entries. Are you sure?", weight=ft.FontWeight.BOLD)
        ], tight=True, spacing=8, width=450, scroll=ft.ScrollMode.AUTO, height=350)

        final_confirm_dialog = create_confirmation_dialog(
            title_text="Confirm Shift Submission", content_control=confirmation_content_column,
            on_confirm=lambda e: self._execute_database_submission(
                reported_online_sales_float, reported_online_payouts_float,
                reported_instant_payouts_float, actual_cash_in_drawer_float,
                sales_item_details),
            on_cancel=lambda ev: self.page.close(self.page.dialog), confirm_button_text="Submit Shift",
            confirm_button_style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_ACCENT_700, color=ft.Colors.WHITE), )
        self.page.dialog = final_confirm_dialog
        self.page.open(final_confirm_dialog)

    def _execute_database_submission(
            self, reported_online_sales_float: float, reported_online_payouts_float: float,
            reported_instant_payouts_float: float, actual_cash_in_drawer_float: float,
            sales_item_details: List[Dict[str, Any]]):
        self.page.close(self.page.dialog)
        if not self.current_user or self.current_user.id is None:
            self.page.open(ft.SnackBar(ft.Text("Critical error: User session invalid."), open=True, bgcolor=ft.Colors.ERROR)); return

        loading_banner = ft.Banner(bgcolor=ft.Colors.AMBER_100,
                                   leading=ft.Icon(ft.Icons.HOURGLASS_TOP_ROUNDED, color=ft.Colors.AMBER_900, size=30),
                                   content=ft.Text("Submitting shift and sales data, please wait...", color=ft.Colors.AMBER_900, weight=ft.FontWeight.BOLD),
                                   actions=[ft.TextButton("Dismiss", disabled=True)] )
        self.page.banner = loading_banner; self.page.banner.open = True; self.page.update()

        try:
            with get_db_session() as db:
                submitted_shift = self.shift_service.create_new_shift_submission(
                    db=db, user_id=self.current_user.id,
                    reported_online_sales_float=reported_online_sales_float,
                    reported_online_payouts_float=reported_online_payouts_float,
                    reported_instant_payouts_float=reported_instant_payouts_float,
                    actual_cash_in_drawer_float=actual_cash_in_drawer_float,
                    sales_item_details=sales_item_details )
            self.page.banner.open = False
            self._open_submission_summary_dialog(submitted_shift)
            self._load_initial_data_for_table()
        except Exception as ex_submit:
            self.page.banner.open = False
            error_detail = f"{type(ex_submit).__name__}: {ex_submit}"
            self.page.open(ft.SnackBar(ft.Text(f"Failed to submit shift: {error_detail}"), open=True, bgcolor=ft.Colors.ERROR, duration=10000))
            print(f"Shift submission execution error: {error_detail}")
        finally:
            if self.scan_input_handler: self.scan_input_handler.focus_input()
            if self.page: self.page.update()


    def _open_submission_summary_dialog(self, submitted_shift: ShiftSubmission):
        calc_drawer_val_dollars = submitted_shift.calculated_drawer_value / 100.0
        delta_online_sales_dollars = submitted_shift.calculated_delta_online_sales / 100.0
        delta_online_payouts_dollars = submitted_shift.calculated_delta_online_payouts / 100.0
        delta_instant_payouts_dollars = submitted_shift.calculated_delta_instant_payouts / 100.0
        drawer_difference_dollars = submitted_shift.drawer_difference / 100.0

        diff_text = f"${abs(drawer_difference_dollars):.2f}"
        diff_label = ""
        diff_color = ft.Colors.BLACK # Default
        if drawer_difference_dollars > 0:
            diff_label = " (Shortfall)"
            diff_color = ft.Colors.RED_ACCENT_700
        elif drawer_difference_dollars < 0:
            diff_label = " (Overage)"
            diff_color = ft.Colors.GREEN_ACCENT_700
        else: # Exactly 0
            diff_label = " (Balanced)"
            # diff_color = ft.Colors.GREEN_ACCENT_700 # Or keep black for balanced

        dialog_content_list = [
            ft.Text("Shift Submission Summary:", weight=ft.FontWeight.BOLD, size=16),
            ft.Text(f"Instant Sales (from table): ${submitted_shift.total_value_instant:.2f}"),
            ft.Text(f"Online Sales Delta: ${delta_online_sales_dollars:.2f}"),
            ft.Text(f"Online Payout Delta: ${delta_online_payouts_dollars:.2f}"),
            ft.Text(f"Instant Payout Delta: ${delta_instant_payouts_dollars:.2f}"),
            ft.Divider(height=5),
            ft.Text(f"Calculated Drawer Value: ${calc_drawer_val_dollars:.2f}", weight=ft.FontWeight.BOLD),
            ft.Text(f"Drawer Difference: {diff_text}{diff_label}", color=diff_color, weight=ft.FontWeight.BOLD, size=14),
            ft.Divider(height=5),
        ]

        dialog = ft.AlertDialog(
            modal=True, # Prevent interaction with background
            title=ft.Text("Shift Submission Successful", weight=ft.FontWeight.BOLD),
            content=ft.Column(dialog_content_list, tight=True, spacing=8, width=350, scroll=ft.ScrollMode.AUTO),
            actions=[ ft.FilledButton("Go to Dashboard", on_click=self._go_to_dashboard, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))) ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=10)
        )

        self.page.dialog = dialog
        self.page.open(dialog)

    def _go_to_dashboard(self, e):
        self.page.close(self.page.dialog)
        self.page.dialog = None
        self._go_back(e)


    def _build_body(self) -> ft.Container:
        self.scan_input_handler = ScanInputHandler(
            scan_text_field=self.scanner_text_field,
            on_scan_complete=self._on_scan_complete_callback,
            on_scan_error=self._on_scan_error_callback,
            require_ticket=True )
        self.sales_items_table_component = SalesEntryItemsTable(
            page_ref=self.page, sales_entry_service=self.sales_entry_service,
            on_item_change_callback=self._update_totals_and_book_counts_properties,
            on_all_items_loaded_callback=self._handle_table_items_loaded )

        reported_totals_row = ft.Row(
            [self.reported_online_sales_field, self.reported_online_payouts_field, self.reported_instant_payouts_field, self.actual_cash_in_drawer_field],
            spacing=10
        )

        info_row = ft.Row(
            [ self.today_date_widget, ft.Container(expand=True), self.books_in_table_count_widget,
              ft.VerticalDivider(width=1, color=ft.Colors.with_opacity(0.3, ft.Colors.ON_SURFACE), thickness=1),
              self.pending_entry_books_count_widget, ],
            alignment=ft.MainAxisAlignment.START, spacing=15, vertical_alignment=ft.CrossAxisAlignment.CENTER )
        top_section = ft.Column(
            [ info_row,
              ft.Text("Enter Cumulative Daily Totals from External Terminal & Actual Cash:", style=ft.TextThemeStyle.TITLE_SMALL, weight=ft.FontWeight.BOLD),
              reported_totals_row,
              ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
              ft.Text("Scan Instant Game Tickets or Enter Next Ticket # Manually:", style=ft.TextThemeStyle.TITLE_SMALL, weight=ft.FontWeight.BOLD),
              ft.Row([self.scanner_text_field], vertical_alignment=ft.CrossAxisAlignment.CENTER), self.scan_error_text_widget
              ], spacing=10 )
        bottom_summary_section = ft.Container(
            ft.Row(
                [ self.total_tickets_sold_widget, self.grand_total_sales_widget,
                  ft.FilledButton( "Submit Shift Sales", icon=ft.Icons.SAVE_AS_ROUNDED, on_click=self._handle_submit_shift_sales_click,
                                   style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE, shape=ft.RoundedRectangleBorder(radius=8)),
                                   height=45, tooltip="Finalize and submit this shift's sales data." )],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER
            ), padding=ft.padding.symmetric(vertical=15, horizontal=5) )
        sales_card_content = ft.Column(
            [top_section, ft.Divider(height=15), self.sales_items_table_component, ft.Divider(height=15), bottom_summary_section],
            spacing=12, expand=True )
        TARGET_CARD_MAX_WIDTH = 1200
        page_width_for_calc = self.page.width if self.page.width and self.page.width > 0 else TARGET_CARD_MAX_WIDTH + 40
        card_effective_width = min(TARGET_CARD_MAX_WIDTH, page_width_for_calc - 40)
        card_effective_width = max(card_effective_width, 750)
        sales_card = ft.Card(
            content=ft.Container(content=sales_card_content, padding=ft.padding.symmetric(vertical=15, horizontal=20), border_radius=ft.border_radius.all(10)),
            elevation=3, width=card_effective_width, )
        return ft.Container(content=sales_card, alignment=ft.alignment.top_center, padding=ft.padding.all(15), expand=True)