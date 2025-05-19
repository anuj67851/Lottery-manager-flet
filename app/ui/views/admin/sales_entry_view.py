import flet as ft
import datetime
from typing import List, Optional, Dict

from app.constants import ADMIN_DASHBOARD_ROUTE, MIN_REQUIRED_SCAN_LENGTH_WITH_TICKET
from app.core.models import User
from app.services.sales_entry_service import SalesEntryService
from app.data.database import get_db_session
from app.core.exceptions import ValidationError, DatabaseError, GameNotFoundError, BookNotFoundError

from app.ui.components.common.appbar_factory import create_appbar
from app.ui.components.common.dialog_factory import create_confirmation_dialog
from app.ui.components.tables.sales_entry_items_table import SalesEntryItemsTable
from app.ui.components.tables.sales_entry_item_data import SalesEntryItemData
from app.ui.components.common.scan_input_handler import ScanInputHandler # New Handler


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

        self.today_date_widget = ft.Text(
            f"Date: {datetime.datetime.now().strftime('%A, %B %d, %Y %I:%M %p')}",
            style=ft.TextThemeStyle.TITLE_MEDIUM,
            weight=ft.FontWeight.BOLD
        )
        self.books_in_table_count_widget = ft.Text(
            "Books In Table: 0", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.NORMAL
        )
        self.pending_entry_books_count_widget = ft.Text(
            "Pending Entry: 0", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.NORMAL, color=ft.Colors.ORANGE_ACCENT_700
        )

        self.scanner_text_field: ft.TextField = ft.TextField( # Initialize TextField here
            label="Scan Full Book Code (e.g., GameNo+BookNo+TicketNo)",
            hint_text=f"Input Game, Book, Ticket numbers for {MIN_REQUIRED_SCAN_LENGTH_WITH_TICKET} chars total.",
            autofocus=True, border_radius=8, prefix_icon=ft.Icons.QR_CODE_SCANNER_ROUNDED,
            expand=True, height=50
        )
        self.scan_input_handler: Optional[ScanInputHandler] = None # Will be initialized in _build_body or after

        self.sales_items_table_component: Optional[SalesEntryItemsTable] = None # Init in _build_body
        self.grand_total_sales_widget = ft.Text("Grand Total Sales: $0", weight=ft.FontWeight.BOLD, size=16)
        self.total_tickets_sold_widget = ft.Text("Total Tickets Sold: 0", weight=ft.FontWeight.BOLD, size=16)
        self.scan_error_text_widget = ft.Text("", color=ft.Colors.RED_ACCENT_700, visible=False, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)

        self.page.appbar = create_appbar(
            page=self.page, router=self.router, title_text=f"{self.current_user.role.capitalize()} > Sales Entry",
            current_user=self.current_user, license_status=self.license_status,
            leading_widget=ft.IconButton(
                icon=ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                tooltip="Go Back to Admin Dashboard",
                icon_color=ft.Colors.WHITE,
                on_click=self._go_back
            )
        )
        self.content = self._build_body() # Builds UI, including initializing ScanInputHandler
        self._load_initial_data_for_table()

    def _go_back(self, e):
        nav_params = {**self.previous_view_params}
        if "current_user" not in nav_params and self.current_user: nav_params["current_user"] = self.current_user
        if "license_status" not in nav_params and self.license_status is not None: nav_params["license_status"] = self.license_status
        self.router.navigate_to(self.previous_view_route, **nav_params)

    def _load_initial_data_for_table(self):
        if self.sales_items_table_component:
            self.sales_items_table_component.load_initial_active_books()

    def _handle_table_items_loaded(self, all_items: List[SalesEntryItemData]):
        self._update_totals_and_book_counts(None) # Pass None or all_items

    def _on_scan_complete_callback(self, parsed_data: Dict[str, str]):
        """Callback for ScanInputHandler on successful scan and parse."""
        self._clear_scan_error() # Clear previous errors
        game_no_str = parsed_data.get('game_no', '')
        book_no_str = parsed_data.get('book_no', '')
        ticket_no_str = parsed_data.get('ticket_no', '') # ticket_no is expected here

        self._process_scan_and_update_table(game_no_str, book_no_str, ticket_no_str)
        # ScanInputHandler will auto-clear and auto-focus by default

    def _on_scan_error_callback(self, error_message: str):
        """Callback for ScanInputHandler on scan/parse error."""
        self.scan_error_text_widget.value = error_message
        self.scan_error_text_widget.visible = True
        if self.scan_error_text_widget.page: self.scan_error_text_widget.update()
        if self.page: self.page.update()
        if self.scan_input_handler: self.scan_input_handler.focus_input()


    def _clear_scan_error(self):
        self.scan_error_text_widget.value = ""
        self.scan_error_text_widget.visible = False
        if self.scan_error_text_widget.page : self.scan_error_text_widget.update()


    def _process_scan_and_update_table(self, game_no_str: str, book_no_str: str, ticket_no_str: str):
        self._clear_scan_error()
        item_data_processed: Optional[SalesEntryItemData] = None
        try:
            # Validation is largely handled by ScanInputHandler, but can double-check here if needed
            # For example, specific business rules not covered by generic parsing.

            with get_db_session() as db:
                book_model_instance = self.sales_entry_service.get_or_create_book_for_sale(db, game_no_str, book_no_str)

            if self.sales_items_table_component:
                item_data_processed = self.sales_items_table_component.add_or_update_book_for_sale(book_model_instance, ticket_no_str)
            else:
                raise Exception("Sales items table component not initialized.")

        except (ValidationError, GameNotFoundError, BookNotFoundError, DatabaseError) as e:
            self._on_scan_error_callback(str(e.message if hasattr(e, 'message') else e))
        except Exception as ex_general:
            self._on_scan_error_callback(f"Error processing scan: {type(ex_general).__name__} - {ex_general}")

        if self.page and self.page.controls: self.page.update() # Ensure UI reflects changes

        # Focus logic: if item processed, focus its text field; otherwise, focus scanner.
        if self.scan_input_handler:
            self.scan_input_handler.focus_input()


    def _update_totals_and_book_counts(self, changed_item_data: Optional[SalesEntryItemData] = None):
        if not self.sales_items_table_component: return

        all_display_items = self.sales_items_table_component.get_all_data_items()
        grand_total_sales_val = sum(item.amount_calculated for item in all_display_items if item.is_processed_for_sale or item.all_tickets_sold_confirmed)
        total_tickets_sold_val = sum(item.tickets_sold_calculated for item in all_display_items if item.is_processed_for_sale or item.all_tickets_sold_confirmed)
        pending_entry_count = sum(1 for item in all_display_items if not item.ui_new_ticket_no_str.strip() and not item.all_tickets_sold_confirmed)

        self.grand_total_sales_widget.value = f"Grand Total Sales: ${grand_total_sales_val}"
        self.total_tickets_sold_widget.value = f"Total Tickets Sold: {total_tickets_sold_val}"
        self.books_in_table_count_widget.value = f"Books In Table: {len(all_display_items)}"
        self.pending_entry_books_count_widget.value = f"Pending Entry: {pending_entry_count}"

        if self.grand_total_sales_widget.page: self.grand_total_sales_widget.update()
        if self.total_tickets_sold_widget.page: self.total_tickets_sold_widget.update()
        if self.books_in_table_count_widget.page: self.books_in_table_count_widget.update()
        if self.pending_entry_books_count_widget.page: self.pending_entry_books_count_widget.update()

    def _handle_submit_all_sales_click(self, e):
        if not self.sales_items_table_component:
            self.page.open(ft.SnackBar(ft.Text("Sales table not ready."), open=True, bgcolor=ft.Colors.ERROR))
            return
        all_current_table_items = self.sales_items_table_component.get_all_data_items()
        if not all_current_table_items:
            self.page.open(ft.SnackBar(ft.Text("No books loaded in the sales table."), open=True))
            return
        items_with_empty_fields: List[SalesEntryItemData] = []
        for item_data in all_current_table_items:
            if not item_data.ui_new_ticket_no_str.strip() and not item_data.all_tickets_sold_confirmed:
                items_with_empty_fields.append(item_data)
        if items_with_empty_fields:
            self._prompt_for_empty_field_books_confirmation(items_with_empty_fields)
        else:
            self._confirm_final_submission()

    def _prompt_for_empty_field_books_confirmation(self, items_to_confirm: List[SalesEntryItemData]):
        book_details_str = "\n".join([f"- Game {item.book_model.game.game_number} / Book {item.book_number} / {item.game_name} / ${item.game_price}" for item in items_to_confirm])
        dialog_content_column = ft.Column(
            [
                ft.Text("The following books have no new ticket number entered:", weight=ft.FontWeight.BOLD),
                ft.Container(ft.Column(controls=[ft.Text(book_details_str, selectable=True)], scroll=ft.ScrollMode.ADAPTIVE), height=min(400, len(items_to_confirm)*26), padding=5),
                ft.Divider(height=10), ft.Text("Do you want to mark them as ALL TICKETS SOLD?"),
                ft.Text("Choosing 'No' will skip these specific books from this submission if their ticket number remains empty.", size=11, italic=True, color=ft.Colors.OUTLINE)
            ], tight=True, spacing=10, width=450
        )
        def _handle_dialog_choice(mark_as_all_sold: bool):
            self.page.close(self.page.dialog)
            if mark_as_all_sold:
                for item_data in items_to_confirm:
                    item_data.confirm_all_sold() # This calls item's on_change, which calls _update_totals_and_book_counts
                    if self.sales_items_table_component: # And also explicitly refresh row in table
                        self.sales_items_table_component.update_datarow_for_item(item_data.unique_id)
            # Ensure totals are up-to-date before final submission prompt
            self._update_totals_and_book_counts()
            self._confirm_final_submission()

        confirm_dialog = ft.AlertDialog(
            modal=True, title=ft.Text("Confirm Unentered Books"), content=dialog_content_column,
            actions=[
                ft.TextButton("Cancel Submission", on_click=lambda _: self.page.close(self.page.dialog)),
                ft.TextButton("No, Skip These Empty", on_click=lambda _: _handle_dialog_choice(False)),
                ft.FilledButton("Yes, Mark All Sold", on_click=lambda _: _handle_dialog_choice(True)),
            ], actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog = confirm_dialog
        self.page.open(confirm_dialog)

    def _confirm_final_submission(self):
        if not self.sales_items_table_component: return
        items_ready_for_db = self.sales_items_table_component.get_all_items_for_submission()
        if not items_ready_for_db:
            self.page.open(ft.SnackBar(ft.Text("No entries are ready for submission."), open=True, duration=5000))
            return

        total_sales_val = sum(item.amount_calculated for item in items_ready_for_db)
        total_tickets_val = sum(item.tickets_sold_calculated for item in items_ready_for_db)

        confirmation_content = ft.Column([
            ft.Text(f"You are about to submit {len(items_ready_for_db)} sales entries."),
            ft.Text(f"Total Tickets in this submission: {total_tickets_val}"),
            ft.Text(f"Total Sales Amount in this submission: ${total_sales_val}"),
            ft.Divider(height=10),
            ft.Text("This action CANNOT be easily reverted. Proceed?", weight=ft.FontWeight.BOLD)
        ], height=130)

        final_confirm_dialog = create_confirmation_dialog(
            title_text="Confirm Sales Submission",
            content_control=confirmation_content,
            on_confirm=self._execute_database_submission,
            on_cancel=lambda ev: self.page.close(self.page.dialog),
            confirm_button_text="Save Sales",
            confirm_button_style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_ACCENT_700, color=ft.Colors.WHITE),
        )
        self.page.dialog = final_confirm_dialog
        self.page.open(final_confirm_dialog)

    def _execute_database_submission(self, e):
        self.page.close(self.page.dialog)
        if not self.sales_items_table_component or not self.current_user or self.current_user.id is None:
            self.page.open(ft.SnackBar(ft.Text("Critical error: Table or user session invalid."), open=True, bgcolor=ft.Colors.ERROR))
            return
        items_payload_for_service = [item.get_data_for_submission() for item in self.sales_items_table_component.get_all_items_for_submission()]
        if not items_payload_for_service:
            self.page.open(ft.SnackBar(ft.Text("No valid sales data to submit after final confirmations."), open=True))
            return
        try:
            with get_db_session() as db:
                sales_saved, books_updated, errors = self.sales_entry_service.process_and_save_sales_batch(
                    db, self.current_user.id, items_payload_for_service
                )
            result_message = f"{sales_saved} sales entries saved. {books_updated} books updated."
            if errors:
                result_message += f"\nEncountered {len(errors)} issues (see console log)."
                print("Sales Submission Errors:", errors)
                self.page.open(ft.SnackBar(
                    content=ft.Column([ft.Text(result_message), ft.Text("Some items had errors. Check console logs.", selectable=True)]),
                    open=True, bgcolor=ft.Colors.AMBER_ACCENT_700, duration=15000
                ))
            else:
                self.page.open(ft.SnackBar(ft.Text(result_message), open=True, bgcolor=ft.Colors.GREEN))

            self._load_initial_data_for_table() # Reload table with fresh data
            # _update_totals_and_book_counts is called by _handle_table_items_loaded
            self._go_back(e) # Navigate back after submission
        except Exception as ex_submit:
            error_detail = f"{type(ex_submit).__name__}: {ex_submit}"
            self.page.open(ft.SnackBar(ft.Text(f"Failed to submit sales: {error_detail}"), open=True, bgcolor=ft.Colors.ERROR, duration=10000))
            print(f"Sales submission execution error: {error_detail}")

    def _build_body(self) -> ft.Container:
        # Initialize ScanInputHandler with the TextField
        self.scan_input_handler = ScanInputHandler(
            scan_text_field=self.scanner_text_field,
            on_scan_complete=self._on_scan_complete_callback,
            on_scan_error=self._on_scan_error_callback,
            require_ticket=True # Sales entry requires game+book+ticket
        )

        self.sales_items_table_component = SalesEntryItemsTable(
            page_ref=self.page, sales_entry_service=self.sales_entry_service,
            on_item_change_callback=self._update_totals_and_book_counts, # Single item changed
            on_all_items_loaded_callback=self._handle_table_items_loaded # All initial items loaded
        )

        info_row = ft.Row(
            [
                self.today_date_widget,
                ft.Container(expand=True),
                self.books_in_table_count_widget,
                ft.VerticalDivider(width=1, color=ft.Colors.with_opacity(0.3, ft.Colors.ON_SURFACE), thickness=1),
                self.pending_entry_books_count_widget,
            ],
            alignment=ft.MainAxisAlignment.START, spacing=15, vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
        top_section = ft.Column(
            [info_row,
             ft.Row([self.scanner_text_field], vertical_alignment=ft.CrossAxisAlignment.CENTER), # Use the class member
             self.scan_error_text_widget], spacing=10
        )
        bottom_summary_section = ft.Container(
            ft.Row(
                [self.total_tickets_sold_widget, self.grand_total_sales_widget,
                 ft.FilledButton(
                     "Submit All Sales", icon=ft.Icons.SAVE_AS_ROUNDED,
                     on_click=self._handle_submit_all_sales_click,
                     style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE, shape=ft.RoundedRectangleBorder(radius=8)),
                     height=45, tooltip="Finalize and save all entered sales data for loaded books."
                 )],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER
            ), padding=ft.padding.symmetric(vertical=15, horizontal=5)
        )
        sales_card_content = ft.Column(
            [top_section, ft.Divider(height=15), self.sales_items_table_component,
             ft.Divider(height=15), bottom_summary_section], spacing=12, expand=True
        )
        TARGET_CARD_MAX_WIDTH = 1200
        page_width_for_calc = self.page.width if self.page.width and self.page.width > 0 else TARGET_CARD_MAX_WIDTH + 40
        card_effective_width = min(TARGET_CARD_MAX_WIDTH, page_width_for_calc - 40)
        card_effective_width = max(card_effective_width, 750)
        sales_card = ft.Card(
            content=ft.Container(
                content=sales_card_content,
                padding=ft.padding.symmetric(vertical=15, horizontal=20),
                border_radius=ft.border_radius.all(10)
            ), elevation=3, width=card_effective_width,
        )
        return ft.Container(content=sales_card, alignment=ft.alignment.top_center, padding=ft.padding.all(15), expand=True)