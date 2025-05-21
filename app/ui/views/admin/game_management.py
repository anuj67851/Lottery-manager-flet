import flet as ft

from app.constants import ADMIN_DASHBOARD_ROUTE, REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER
from app.core import ValidationError, DatabaseError, GameNotFoundError # These exceptions are now handled more explicitly
from app.core.models import User
from app.data.database import get_db_session
from app.services.game_service import GameService # GameService has enhanced validation
from app.ui.components.tables.games_table import GamesTable
from app.ui.components.widgets.number_decimal_input import NumberDecimalField
from app.ui.components.common.appbar_factory import create_appbar
from app.ui.components.common.search_bar_component import SearchBarComponent
from app.ui.components.common.dialog_factory import create_form_dialog


class GameManagementView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user: User, license_status: bool,
                 previous_view_route: str = ADMIN_DASHBOARD_ROUTE,
                 previous_view_params: dict = None,
                 **params):
        super().__init__(expand=True, padding=0)
        self.game_service = GameService()
        self.page = page
        self.router = router
        self.current_user = current_user
        self.license_status = license_status

        self.total_games_widget = ft.Text("", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD)
        self.active_games_widget = ft.Text("", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)
        self.expired_games_widget = ft.Text("", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_700)

        self.previous_view_route = previous_view_route
        self.previous_view_params = previous_view_params if previous_view_params is not None else {}

        self.games_table_component = GamesTable(
            page=self.page,
            game_service=self.game_service,
            on_data_changed_stats=self._handle_table_data_stats_change,
        )

        self.search_bar = SearchBarComponent(
            on_search_changed=self._on_search_term_changed,
            label="Search Games (Name, No., Price, Tickets, Value)",
            expand=True
        )

        self.page.appbar = create_appbar(
            page=self.page, router=self.router, title_text=f"{self.current_user.role.capitalize()} > Game Management",
            current_user=self.current_user, license_status=self.license_status,
            leading_widget=ft.IconButton(icon=ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED, tooltip="Go Back", icon_color=ft.Colors.WHITE, on_click=self._go_back)
        )
        self.content = self._build_body()
        self.games_table_component.refresh_data_and_ui()

    def _on_search_term_changed(self, search_term: str):
        self.games_table_component.refresh_data_and_ui(search_term=search_term)

    def _go_back(self, e):
        nav_params = {**self.previous_view_params}
        if "current_user" not in nav_params and self.current_user: nav_params["current_user"] = self.current_user
        if "license_status" not in nav_params and self.license_status is not None: nav_params["license_status"] = self.license_status
        self.router.navigate_to(self.previous_view_route, **nav_params)

    def _build_body(self) -> ft.Container:
        stats_row = ft.Row([self.total_games_widget, ft.VerticalDivider(width=1, color=ft.Colors.with_opacity(0.5, ft.Colors.OUTLINE)), self.active_games_widget, ft.VerticalDivider(width=1, color=ft.Colors.with_opacity(0.5, ft.Colors.OUTLINE)), self.expired_games_widget], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=15)
        actions_row = ft.Row([self.search_bar, ft.FilledButton("Add New Game", icon=ft.Icons.ADD_ROUNDED, on_click=self._handle_add_game_click, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)), height=48)], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=15)
        game_management_card_content = ft.Column(controls=[ft.Text("Game Configuration & Overview", style=ft.TextThemeStyle.HEADLINE_SMALL, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.LEFT), ft.Divider(height=10), stats_row, ft.Divider(height=20), actions_row, ft.Divider(height=15, color=ft.Colors.TRANSPARENT), self.games_table_component], spacing=15, expand=True)
        TARGET_CARD_MAX_WIDTH = 1200
        page_width_for_calc = self.page.width if self.page.width and self.page.width > 0 else TARGET_CARD_MAX_WIDTH + 40
        card_effective_width = min(TARGET_CARD_MAX_WIDTH, page_width_for_calc - 40)
        game_management_card = ft.Card(content=ft.Container(content=game_management_card_content, padding=20, border_radius=ft.border_radius.all(10)), elevation=2, width=card_effective_width)
        return ft.Container(content=game_management_card, alignment=ft.alignment.top_center, padding=20, expand=True)

    def _close_active_dialog(self, e=None):
        if self.page.dialog: self.page.close(self.page.dialog); self.page.update()

    def _handle_add_game_click(self, e):
        # UI fields for the dialog
        game_name_field = ft.TextField(label="Game Name", autofocus=True, border_radius=8, hint_text="e.g., Super Cash Blast")
        # NumberDecimalField's get_value_as_float/int handles conversion and basic None check
        price_field = NumberDecimalField(label="Price (e.g., $1.00)", hint_text="e.g., 1.00 or 2.50", is_money_field=True, currency_symbol="$", is_integer_only=False, border_radius=8)
        total_tickets_field = NumberDecimalField(label="Total Tickets Per Book", is_integer_only=True, border_radius=8, hint_text="e.g., 150")
        game_number_field = NumberDecimalField(label="Game No. (e.g., 3 digits)", is_integer_only=True, border_radius=8, hint_text="e.g., 453")
        ticket_order_options = [ft.dropdown.Option(order, order.capitalize()) for order in [REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER]]
        ticket_order_dropdown = ft.Dropdown(label="Default Ticket Order", options=ticket_order_options, value=REVERSE_TICKET_ORDER, border_radius=8)
        error_text_add = ft.Text(visible=False, color=ft.Colors.RED_700)

        form_column = ft.Column([game_name_field, game_number_field, price_field, total_tickets_field, ticket_order_dropdown, error_text_add], tight=True, spacing=15, scroll=ft.ScrollMode.AUTO)

        def _save_new_game_handler(ev):
            error_text_add.value = ""; error_text_add.visible = False # Reset error
            try:
                game_name = game_name_field.value
                price_dollars = price_field.get_value_as_float() # Returns float or None
                total_tickets = total_tickets_field.get_value_as_int() # Returns int or None
                game_number = game_number_field.get_value_as_int() # Returns int or None
                order = ticket_order_dropdown.value

                # Service layer will now perform detailed validation
                # Basic None checks can still be useful here for immediate UI feedback if desired,
                # but service layer is the definitive validator.
                if price_dollars is None: raise ValidationError("Price is required and must be a valid number.")
                if total_tickets is None: raise ValidationError("Total Tickets is required and must be a whole number.")
                if game_number is None: raise ValidationError("Game Number is required and must be a whole number.")

                with get_db_session() as db:
                    self.game_service.create_game(db, game_name, price_dollars, total_tickets, game_number, order)

                self._close_active_dialog()
                self.page.open(ft.SnackBar(ft.Text(f"Game '{game_name}' (No: {game_number}) created successfully!"), open=True))
                self.games_table_component.refresh_data_and_ui(self.search_bar.get_value())
            except (ValidationError, DatabaseError, GameNotFoundError) as ex: # Catch specific errors from service
                error_text_add.value = str(ex.message if hasattr(ex, 'message') else ex)
                error_text_add.visible = True
            except Exception as ex_general: # Catch any other unexpected error
                error_text_add.value = f"An unexpected error occurred: {type(ex_general).__name__} - {ex_general}"
                error_text_add.visible = True
            if error_text_add.page: error_text_add.update()


        add_game_dialog = create_form_dialog(
            page=self.page, title_text="Add New Game", form_content_column=form_column,
            on_save_callback=_save_new_game_handler, on_cancel_callback=self._close_active_dialog, min_width=450
        )
        self.page.dialog = add_game_dialog; self.page.open(self.page.dialog)

    def _handle_table_data_stats_change(self, total_games: int, active_games: int, expired_games: int):
        self.total_games_widget.value = f"Total Games: {total_games}"
        self.active_games_widget.value = f"Active: {active_games}"
        self.expired_games_widget.value = f"Expired: {expired_games}"
        if self.total_games_widget.page: self.total_games_widget.update()
        if self.active_games_widget.page: self.active_games_widget.update()
        if self.expired_games_widget.page: self.expired_games_widget.update()