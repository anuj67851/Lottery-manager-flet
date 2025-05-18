import flet as ft
import datetime
from typing import List, Optional, Dict, Any

from app.constants import ADMIN_DASHBOARD_ROUTE, MIN_REQUIRED_SCAN_LENGTH, GAME_LENGTH, BOOK_LENGTH, TICKET_LENGTH
from app.core.models import User, Book as BookModel
from app.services.sales_entry_service import SalesEntryService
from app.data.database import get_db_session
from app.core.exceptions import ValidationError, DatabaseError, GameNotFoundError, BookNotFoundError

from app.ui.components.common.appbar_factory import create_appbar
from app.ui.components.common.dialog_factory import create_confirmation_dialog
from app.ui.components.tables.sales_entry_items_table import SalesEntryItemsTable
from app.ui.components.tables.sales_entry_item_data import SalesEntryItemData
from app.config import APP_TITLE

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
        self.books_in_table_count_widget = ft.Text( # Renamed for clarity
            "Books In Table: 0",
            style=ft.TextThemeStyle.TITLE_MEDIUM,
            weight=ft.FontWeight.NORMAL
        )
        self.pending_entry_books_count_widget = ft.Text( # New widget
            "Pending Entry: 0",
            style=ft.TextThemeStyle.TITLE_MEDIUM,
            weight=ft.FontWeight.NORMAL,
            color=ft.Colors.ORANGE_ACCENT_700 # Highlight pending
        )
        self.scanner_input_field: Optional[ft.TextField] = None
        self.sales_items_table_component: Optional[SalesEntryItemsTable] = None
        self.grand_total_sales_widget = ft.Text("Grand Total Sales: $0", weight=ft.FontWeight.BOLD, size=16)
        self.total_tickets_sold_widget = ft.Text("Total Tickets Sold: 0", weight=ft.FontWeight.BOLD, size=16)
        self.scan_error_text_widget = ft.Text("", color=ft.Colors.RED_ACCENT_700, visible=False, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)

        self.page.appbar = create_appbar(
            page=self.page, router=self.router, title_text=f"{APP_TITLE} > Sales Entry",
            current_user=self.current_user, license_status=self.license_status,
            leading_widget=ft.IconButton(
                icon=ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                tooltip="Go Back to Admin Dashboard",
                icon_color=ft.Colors.WHITE,
                on_click=self._go_back
            )
        )
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

    def _handle_table_items_loaded(self, all_items: List[SalesEntryItemData]):
        self._update_totals_and_book_counts(all_items) # Use combined method name

    def _handle_scanner_input_change(self, e: ft.ControlEvent):
        if not self.scanner_input_field: return
        current_value = self.scanner_input_field.value.strip() if self.scanner_input_field.value else ""
        if len(current_value) >= MIN_REQUIRED_SCAN_LENGTH: # Assuming MIN_REQUIRED_SCAN_LENGTH is sum of GAME+BOOK+TICKET
            parsed_data = current_value[:MIN_REQUIRED_SCAN_LENGTH]
            self._process_scan_and_update_table(parsed_data)
            self.scanner_input_field.value = ""
            if self.scanner_input_field.page : self.scanner_input_field.update()

    def _process_scan_and_update_table(self, scanned_data_segment: str):
        self.scan_error_text_widget.value = ""
        self.scan_error_text_widget.visible = False
        if self.scan_error_text_widget.page and self.page.controls:
            self.scan_error_text_widget.update()

        item_data_processed: Optional[SalesEntryItemData] = None
        try:
            game_no_str = scanned_data_segment[:GAME_LENGTH]
            book_no_str = scanned_data_segment[GAME_LENGTH: GAME_LENGTH + BOOK_LENGTH]
            ticket_no_str = scanned_data_segment[GAME_LENGTH + BOOK_LENGTH: GAME_LENGTH + BOOK_LENGTH + TICKET_LENGTH]

            if not (game_no_str.isdigit() and len(game_no_str) == GAME_LENGTH):
                raise ValidationError(f"Invalid Game No. in scan: '{game_no_str}'.")
            if not (book_no_str.isdigit() and len(book_no_str) == BOOK_LENGTH):
                raise ValidationError(f"Invalid Book No. in scan: '{book_no_str}'.")
            if not (ticket_no_str.isdigit() and len(ticket_no_str) == TICKET_LENGTH): # Enforce exact length
                raise ValidationError(f"Invalid Ticket No. in scan: '{ticket_no_str}'. Expected {TICKET_LENGTH} digits.")

            with get_db_session() as db:
                book_model_instance = self.sales_entry_service.get_or_create_book_for_sale(db, game_no_str, book_no_str)
            if self.sales_items_table_component:
                item_data_processed = self.sales_items_table_component.add_or_update_book_for_sale(book_model_instance, ticket_no_str)
            else: raise Exception("Sales items table component not initialized.")
        except (ValidationError, GameNotFoundError, BookNotFoundError, DatabaseError) as e:
            self.scan_error_text_widget.value = str(e.message if hasattr(e, 'message') else e)
            self.scan_error_text_widget.visible = True
        except Exception as ex_general:
            self.scan_error_text_widget.value = f"Error processing scan: {type(ex_general).__name__} - {ex_general}"
            self.scan_error_text_widget.visible = True
        if self.scan_error_text_widget.page and self.page.controls:
            self.scan_error_text_widget.update()
        if self.page and self.page.controls:
            self.page.update()
        if item_data_processed and item_data_processed.ui_new_ticket_no_ref:
            if item_data_processed.ui_new_ticket_no_ref.page:
                item_data_processed.ui_new_ticket_no_ref.focus()
            else:
                if self.scanner_input_field and self.scanner_input_field.page : self.scanner_input_field.focus()
        elif self.scanner_input_field and self.scanner_input_field.page :
            self.scanner_input_field.focus()

    def _update_totals_and_book_counts(self, changed_item_data: Optional[SalesEntryItemData] = None): # Renamed
        if not self.sales_items_table_component: return

        all_display_items = self.sales_items_table_component.get_all_data_items()

        grand_total_sales_val = sum(item.amount_calculated for item in all_display_items if item.is_processed_for_sale or item.all_tickets_sold_confirmed)
        total_tickets_sold_val = sum(item.tickets_sold_calculated for item in all_display_items if item.is_processed_for_sale or item.all_tickets_sold_confirmed)

        # Calculate books pending entry
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
                ft.Column(controls=[ft.Text(book_details_str, selectable=True)], height=150, scroll=ft.ScrollMode.ADAPTIVE),
                ft.Divider(height=10), ft.Text("Do you want to mark them as ALL TICKETS SOLD?"),
                ft.Text("Choosing 'No' will skip these specific books from this submission if their ticket number remains empty.", size=11, italic=True, color=ft.Colors.OUTLINE)
            ], tight=True, spacing=10, width=450
        )
        def _handle_dialog_choice(mark_as_all_sold: bool):
            self.page.close(self.page.dialog)
            if mark_as_all_sold:
                for item_data in items_to_confirm:
                    item_data.confirm_all_sold()
                    if self.sales_items_table_component:
                        self.sales_items_table_component.update_datarow_for_item(item_data.unique_id)
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
        final_confirm_dialog = create_confirmation_dialog(
            title_text="Confirm Sales Submission",
            content_control=ft.Text(f"Proceed to save {len(items_ready_for_db)} processed sales entries and update book statuses? This action CANNOT be easily reverted."),
            on_confirm=self._execute_database_submission,
            on_cancel=lambda ev: self.page.close(self.page.dialog),
            confirm_button_text="Save Sales",
            confirm_button_style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_ACCENT_700, color=ft.Colors.WHITE)
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
            self._load_initial_data_for_table()
            self._update_totals_and_book_counts()
            self._go_back(e)
        except Exception as ex_submit:
            error_detail = f"{type(ex_submit).__name__}: {ex_submit}"
            self.page.open(ft.SnackBar(ft.Text(f"Failed to submit sales: {error_detail}"), open=True, bgcolor=ft.Colors.ERROR, duration=10000))
            print(f"Sales submission execution error: {error_detail}")

    def _build_body(self) -> ft.Container:
        self.scanner_input_field = ft.TextField(
            label="Scan Full Book Code (e.g., GameNo+BookNo+TicketNo)",
            hint_text=f"Input Game({GAME_LENGTH}), Book({BOOK_LENGTH}), Ticket({TICKET_LENGTH}) numbers.",
            on_change=self._handle_scanner_input_change,
            autofocus=True, border_radius=8, prefix_icon=ft.Icons.QR_CODE_SCANNER_ROUNDED,
            expand=True, height=50
        )
        self.sales_items_table_component = SalesEntryItemsTable(
            page_ref=self.page, sales_entry_service=self.sales_entry_service,
            on_item_change_callback=self._update_totals_and_book_counts,
            on_all_items_loaded_callback=self._handle_table_items_loaded
        )

        # Modified info_row for alignment
        info_row = ft.Row(
            [
                self.today_date_widget,
                # Use an expanding spacer to push counts to the right
                ft.Container(expand=True),
                self.books_in_table_count_widget,
                ft.VerticalDivider(width=1, color=ft.Colors.with_opacity(0.3, ft.Colors.ON_SURFACE), thickness=1),
                self.pending_entry_books_count_widget,
            ],
            alignment=ft.MainAxisAlignment.START, # Start for date, end for counts due to spacer
            spacing=15, # Adjusted spacing
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

        top_section = ft.Column(
            [info_row,
             ft.Row([self.scanner_input_field], vertical_alignment=ft.CrossAxisAlignment.CENTER),
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