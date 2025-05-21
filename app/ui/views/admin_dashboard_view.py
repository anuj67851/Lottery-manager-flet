from typing import List, Dict, Tuple, Any

import flet as ft
from sqlalchemy.orm import Session

from app.constants import (
    GAME_MANAGEMENT_ROUTE, ADMIN_DASHBOARD_ROUTE, BOOK_MANAGEMENT_ROUTE,
    SALES_ENTRY_ROUTE, BOOK_ACTION_FULL_SALE, BOOK_ACTION_ACTIVATE,
    ADMIN_USER_MANAGEMENT_ROUTE, SALES_BY_DATE_REPORT_ROUTE, GAME_EXPIRY_REPORT_ROUTE,
    BOOK_OPEN_REPORT_ROUTE, STOCK_LEVELS_REPORT_ROUTE
)
from app.core import BookNotFoundError
from app.core.models import User
from app.services import BookService, SalesEntryService, GameService, BackupService, ShiftService
from app.ui.components.common.appbar_factory import create_appbar
from app.ui.components.dialogs.book_action_dialog import BookActionDialog
from app.ui.components.widgets.function_button import create_nav_card_button


class AdminDashboardView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user: User, license_status: bool, **params):
        super().__init__(expand=True)
        self.page = page
        self.router = router
        self.current_user = current_user
        self.license_status = license_status

        self.book_service = BookService()
        self.sales_entry_service = SalesEntryService()
        self.game_service = GameService()
        self.backup_service = BackupService()
        self.shift_service = ShiftService()

        self.navigation_params_for_children = {
            "current_user": self.current_user,
            "license_status": self.license_status,
            "previous_view_route": ADMIN_DASHBOARD_ROUTE,
            "previous_view_params": {
                "current_user": self.current_user,
                "license_status": self.license_status,
            },
        }

        self.page.appbar = create_appbar(
            page=self.page,
            router=self.router,
            title_text="Admin Dashboard",
            current_user=self.current_user,
            license_status=self.license_status
        )
        self.content = self._build_body()

    def _create_section_quadrant(self, title: str, title_color: str,
                                 button_row_controls: list, gradient_colors: list) -> ft.Container:
        scrollable_content = ft.Column(
            controls=[
                ft.Text(
                    title,
                    weight=ft.FontWeight.BOLD,
                    size=20,
                    color=title_color,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Row(
                    controls=button_row_controls,
                    spacing=10,
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    wrap=True,
                ),
            ],
            spacing=15,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.ADAPTIVE,
        )
        quadrant_container = ft.Container(
            content=scrollable_content,
            padding=15,
            border_radius=ft.border_radius.all(10),
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=gradient_colors,
            ),
            expand=True,
            alignment=ft.alignment.center,
        )
        return quadrant_container


    def _process_full_book_sale_batch(self, db: Session, items_to_process: List[Dict[str, Any]], current_user: User) -> Tuple[int, int, List[str]]:
        book_ids_to_sell_this_batch: List[int] = []
        pre_check_errors: List[str] = []

        for item_data in items_to_process:
            book_id = item_data.get('book_id')
            game_number = item_data.get('game_number_str', 'N/A')
            book_number = item_data.get('book_number_str', 'N/A')

            if book_id is None:
                pre_check_errors.append(f"Book {game_number}-{book_number}: Could not identify existing book ID for full sale.")
                continue
            book_ids_to_sell_this_batch.append(book_id)

        if pre_check_errors:
            return 0, len(items_to_process), pre_check_errors

        if not book_ids_to_sell_this_batch:
            return 0, 0, ["No valid books selected for full sale."]

        try:
            _created_shift, successful_sales_count, error_messages = \
                self.shift_service.create_shift_for_admin_full_book_sales(
                    db=db,
                    admin_user_id=current_user.id,
                    book_ids_to_sell=book_ids_to_sell_this_batch
                )
            failure_count = len(book_ids_to_sell_this_batch) - successful_sales_count
            return successful_sales_count, failure_count, error_messages
        except Exception as e_service_call:
            return 0, len(book_ids_to_sell_this_batch), [f"Service error processing full book sales: {str(e_service_call)}"]

    def _process_activate_book_batch(self, db: Session, items_to_process: List[Dict[str, Any]], current_user: User) -> Tuple[int, int, List[str]]:
        success_count = 0
        failure_count = 0
        error_messages: List[str] = []
        book_ids_to_activate = []

        for item_data in items_to_process:
            book_number = item_data['book_number_str']
            game_number = item_data['game_number_str']
            game_id = item_data['game_id']
            try:
                book_model = self.book_service.get_book_by_game_and_book_number(db, game_id, book_number)
                if not book_model:
                    raise BookNotFoundError(f"Book {game_number}-{book_number} not found for activation.")
                book_ids_to_activate.append(book_model.id)
            except Exception as e:
                failure_count +=1
                error_messages.append(f"Book {game_number}-{book_number} pre-check failed: {e}")

        if book_ids_to_activate:
            activated_books, activation_errors = self.book_service.activate_books_batch(db, book_ids_to_activate)
            success_count += len(activated_books)
            failure_count += len(activation_errors)
            error_messages.extend(activation_errors)
        return success_count, failure_count, error_messages


    def _open_full_book_sale_dialog(self, e: ft.ControlEvent):
        dialog = BookActionDialog(
            page_ref=self.page,
            current_user_ref=self.current_user,
            dialog_title="Process Full Book Sale",
            action_button_text="Mark Books as Sold",
            action_type=BOOK_ACTION_FULL_SALE,
            on_confirm_batch_callback=self._process_full_book_sale_batch,
            game_service=self.game_service,
            book_service=self.book_service,
            require_ticket_scan=False
        )
        dialog.open_dialog()


    def _open_activate_book_dialog(self, e: ft.ControlEvent):
        dialog = BookActionDialog(
            page_ref=self.page,
            current_user_ref=self.current_user,
            dialog_title="Activate Books",
            action_button_text="Activate Selected Books",
            action_type=BOOK_ACTION_ACTIVATE,
            on_confirm_batch_callback=self._process_activate_book_batch,
            game_service=self.game_service,
            book_service=self.book_service,
            require_ticket_scan=False
        )
        dialog.open_dialog()

    def _handle_backup_database_click(self, e: ft.ControlEvent):
        # Disable button to prevent multiple clicks while processing
        backup_button: ft.Card = e.control.data # Assuming the card is passed as data or find it another way
        if isinstance(backup_button, ft.Card) and isinstance(backup_button.content, ft.Container):
            backup_button.content.disabled = True # type: ignore
            if backup_button.page: backup_button.update()


        self.page.splash = ft.ProgressBar(visible=True) # Show loading indicator
        self.page.update()

        try:
            success, message = self.backup_service.create_database_backup()
            if success:
                self.page.open(ft.SnackBar(
                    ft.Text(f"Database backup successful! Saved to: {message}"),
                    open=True,
                    bgcolor=ft.Colors.GREEN_ACCENT_700,
                    duration=5000
                ))
            else:
                self.page.open(ft.SnackBar(
                    ft.Text(f"Database backup failed: {message}"),
                    open=True,
                    bgcolor=ft.Colors.RED_ACCENT_700,
                    duration=7000 # Longer for errors
                ))
        except Exception as ex:
            self.page.open(ft.SnackBar(
                ft.Text(f"An unexpected error occurred during backup: {ex}"),
                open=True,
                bgcolor=ft.Colors.ERROR,
                duration=7000
            ))
        finally:
            self.page.splash = None # Hide loading indicator
            if isinstance(backup_button, ft.Card) and isinstance(backup_button.content, ft.Container):
                backup_button.content.disabled = False # type: ignore
                if backup_button.page: backup_button.update()
            self.page.update()


    def _build_sales_functions_quadrant(self) -> ft.Container:
        buttons = [
            create_nav_card_button(
                router=self.router, text="Sales Entry", icon_name=ft.Icons.POINT_OF_SALE_ROUNDED,
                accent_color=ft.Colors.GREEN_700, navigate_to_route=SALES_ENTRY_ROUTE, tooltip="Add Daily Sales",
                router_params=self.navigation_params_for_children),
            create_nav_card_button(
                router=self.router, text="Full Book Sale", icon_name=ft.Icons.BOOK_ONLINE_ROUNDED,
                accent_color=ft.Colors.BLUE_700, tooltip="Mark entire books as sold",
                on_click_override=self._open_full_book_sale_dialog),
            create_nav_card_button(
                router=self.router, text="Activate Book", icon_name=ft.Icons.AUTO_STORIES_ROUNDED,
                accent_color=ft.Colors.TEAL_700, tooltip="Activate specific books for sales",
                on_click_override=self._open_activate_book_dialog),
        ]
        return self._create_section_quadrant(
            title="Sale Functions", title_color=ft.Colors.CYAN_900,
            button_row_controls=buttons,
            gradient_colors=[ft.Colors.CYAN_50, ft.Colors.LIGHT_BLUE_100]
        )

    def _build_inventory_functions_quadrant(self) -> ft.Container:
        buttons = [
            create_nav_card_button(
                router=self.router, text="Manage Games", icon_name=ft.Icons.SPORTS_ESPORTS_ROUNDED,
                accent_color=ft.Colors.DEEP_PURPLE_600, navigate_to_route=GAME_MANAGEMENT_ROUTE,
                tooltip="View, edit, or add game types", router_params=self.navigation_params_for_children,
            ),
            create_nav_card_button(
                router=self.router, text="Manage Books", icon_name=ft.Icons.MENU_BOOK_ROUNDED,
                accent_color=ft.Colors.BROWN_600, navigate_to_route=BOOK_MANAGEMENT_ROUTE,
                tooltip="View, edit, or add lottery ticket books", router_params=self.navigation_params_for_children,
            ),
        ]
        return self._create_section_quadrant(
            title="Inventory Control", title_color=ft.Colors.GREEN_800,
            button_row_controls=buttons,
            gradient_colors=[ft.Colors.GREEN_100, ft.Colors.LIGHT_GREEN_200]
        )

    def _build_report_functions_quadrant(self) -> ft.Container:
        buttons = [
            create_nav_card_button(
                router=self.router, text="Sales by Date", icon_name=ft.Icons.CALENDAR_MONTH_ROUNDED,
                accent_color=ft.Colors.ORANGE_700, navigate_to_route=SALES_BY_DATE_REPORT_ROUTE,
                tooltip="View sales report filtered by date and user", disabled=False,
                router_params=self.navigation_params_for_children),
            create_nav_card_button(
                router=self.router, text="Open Books Report", icon_name=ft.Icons.ASSESSMENT_OUTLINED,
                accent_color=ft.Colors.INDIGO_400, navigate_to_route=BOOK_OPEN_REPORT_ROUTE,
                tooltip="Report on currently open/active books", disabled=False,
                router_params=self.navigation_params_for_children),
            create_nav_card_button(
                router=self.router, text="Game Expiry Report", icon_name=ft.Icons.EVENT_BUSY_OUTLINED,
                accent_color=ft.Colors.DEEP_ORANGE_700, navigate_to_route=GAME_EXPIRY_REPORT_ROUTE,
                tooltip="Report on game expiration dates", disabled=False,
                router_params=self.navigation_params_for_children),
            create_nav_card_button(
                router=self.router, text="Stock Levels Report", icon_name=ft.Icons.INVENTORY_2_OUTLINED,
                accent_color=ft.Colors.BROWN_500, navigate_to_route=STOCK_LEVELS_REPORT_ROUTE,
                tooltip="Report on book stock levels per game", disabled=False,
                router_params=self.navigation_params_for_children),
        ]
        return self._create_section_quadrant(
            title="Data & Reports", title_color=ft.Colors.AMBER_900,
            button_row_controls=buttons,
            gradient_colors=[ft.Colors.AMBER_50, ft.Colors.YELLOW_100]
        )

    def _build_management_functions_quadrant(self) -> ft.Container:
        backup_button_card = create_nav_card_button(
            router=self.router, text="Backup Database", icon_name=ft.Icons.SETTINGS_BACKUP_RESTORE_ROUNDED,
            accent_color=ft.Colors.BLUE_800,
            on_click_override=self._handle_backup_database_click, # Click override
            tooltip="Create a backup of the application database", disabled=False
        )
        # Store the card itself or its clickable container in data to disable/enable it
        if isinstance(backup_button_card.content, ft.Container):
            backup_button_card.content.data = backup_button_card # Pass the card to itself for access

        buttons = [
            create_nav_card_button(
                router=self.router, text="Manage Users", icon_name=ft.Icons.MANAGE_ACCOUNTS_ROUNDED,
                accent_color=ft.Colors.INDIGO_700, navigate_to_route=ADMIN_USER_MANAGEMENT_ROUTE,
                router_params=self.navigation_params_for_children,
                tooltip="Manage Admin and Employee accounts", disabled=False),
            backup_button_card, # Use the created card
        ]
        return self._create_section_quadrant(
            title="System Management", title_color=ft.Colors.DEEP_PURPLE_800,
            button_row_controls=buttons,
            gradient_colors=[ft.Colors.DEEP_PURPLE_50, ft.Colors.INDIGO_100]
        )

    def _build_body(self) -> ft.Column:
        divider_color = ft.Colors.with_opacity(0.3, ft.Colors.ON_SURFACE)
        divider_thickness = 2
        row1 = ft.Row(
            controls=[
                self._build_sales_functions_quadrant(),
                self._build_inventory_functions_quadrant(),
            ],
            spacing=10, expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH
        )
        row2 = ft.Row(
            controls=[
                self._build_report_functions_quadrant(),
                self._build_management_functions_quadrant(),
            ],
            spacing=10, expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH
        )
        return ft.Column(
            controls=[row1, ft.Divider(height=divider_thickness, thickness=divider_thickness, color=divider_color), row2],
            spacing=10, expand=True,
        )