import flet as ft

from app.constants import LOGIN_ROUTE, ADMIN_DASHBOARD_ROUTE, \
    REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER  # Assuming ADMIN_DASHBOARD_ROUTE is where you go back to
from app.core import ValidationError, DatabaseError
from app.data.database import get_db_session
from app.services.game_service import GameService
from app.ui.components.tables.games_table import GamesTable
from app.ui.components.widgets.number_decimal_input import NumberDecimalField


class GameManagementView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user, license_status,
                 previous_view_route: str = ADMIN_DASHBOARD_ROUTE,
                 previous_view_params: dict = None,
                 **params):
        super().__init__(expand=True)
        self.game_service = GameService()
        self.page = page
        self.router = router
        self.current_user = current_user
        self.license_status = license_status
        self.total_games = 0

        # Store the route and params for the "Go Back" functionality
        self.previous_view_route = previous_view_route
        self.previous_view_params = previous_view_params if previous_view_params is not None else {}

        self.games_table_component = GamesTable(
            page=self.page,
            on_data_changed=self._handle_table_data_change,
            game_service=self.game_service
        )

        self.page.appbar = self._build_appbar()
        self.content = self._build_body()

    def logout(self, e):
        self.current_user = None
        self.router.navigate_to(LOGIN_ROUTE)

    def _go_back(self, e):
        """Handles the click event for the back button."""
        self.router.navigate_to(self.previous_view_route, **self.previous_view_params)


    def _build_appbar(self):
        return ft.AppBar(
            # Adding the back button as the leading action
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED, # A common back icon
                tooltip="Go Back",
                icon_color=ft.Colors.WHITE,
                on_click=self._go_back,
            ),
            leading_width=70, # Give some space for the back button
            title=ft.Text("Admin Dashboard > Game Management"),
            bgcolor=ft.Colors.BLUE_700,
            color=ft.Colors.WHITE,
            actions=[
                ft.Text(f"Current User: {self.current_user.username}", weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE),
                ft.Container(width=20),
                ft.Text(f"License: {'Active' if self.license_status else 'Inactive'}", weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE),
                ft.Container(width=20),
                ft.IconButton(
                    icon=ft.Icons.LOGOUT,
                    tooltip="Logout",
                    icon_color=ft.Colors.WHITE,
                    on_click=self.logout,
                ),
            ],
        )

    def _build_body(self):
        game_management_section = ft.Card(
            elevation=4,
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("Game Management", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD, expand=True),
                                ft.Text(f"Total Games: {self.total_games}", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD),
                                ft.Text(f"Active Games: {self.active_games}", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD),
                                ft.Text(f"Expired Games: {self.expired_games}", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD),
                                ft.FilledButton(
                                    "Add New Game",
                                    icon=ft.Icons.GAMEPAD_OUTLINED, # Kept icon
                                    on_click=self._handle_add_game_click,
                                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT), # Spacer
                        self.games_table_component, # The GamesTable instance
                    ],
                    spacing=15,
                ),
                padding=20,
                border_radius=8,
                expand=True, # Allow user management to take more space
                bgcolor=ft.Colors.WHITE70,
            ),
            expand=True # Card expands
        )
        return ft.Column(
            [
                game_management_section,
            ],
            spacing=20, # Spacing between major sections
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER, # Stretch cards to fill width
            scroll=ft.ScrollMode.ADAPTIVE, # Add scroll if content overflows
            width=self.page.width / 1.5,
        )

    def _handle_add_game_click(self, e):
        self._open_add_game_dialog()

    def _open_add_game_dialog(self):
        def _save_new_game(e):
            error_text_add.value = ""
            error_text_add.visible = False

            game_name = game_name_field.value.strip()
            price = price_field.get_value_as_int()
            total_tickets = total_tickets_field.get_value_as_int()
            order = ticket_order_dropdown.value
            game_number = game_number_field.get_value_as_int()

            if not game_name or not price or not total_tickets or not order or not game_number:
                error_text_add.value = "All fields are required."
                error_text_add.visible = True
                error_text_add.update()
                self.page.update()
                return

            try:
                with get_db_session() as db:
                    self.game_service.create_game(db, game_name, price, total_tickets, game_number, order)
                self.page.open(ft.SnackBar(ft.Text(f"Book '{game_number} -- {game_name}' created successfully!"), open=True))
                self._close_dialog()
                self.games_table_component.refresh_data()
            except (ValidationError, DatabaseError) as ex:
                error_text_add.value = str(ex)
                error_text_add.visible = True
            except Exception as ex_general:
                error_text_add.value = f"An unexpected error occurred: {ex_general}"
                error_text_add.visible = True

            error_text_add.update()
            self.page.update()

        game_name_field = ft.TextField(label="Game Name", autofocus=True, border_radius=8)
        price_field = NumberDecimalField(
            label="Amount (in $)",
            hint_text="e.g., 10",
            is_money_field=True,  # Indicate this is a money field
            currency_symbol="$",  # Specify the currency symbol
            is_integer_only=False,
        )
        total_tickets_field = NumberDecimalField(label="Total Tickets", is_integer_only=True, border_radius=8, hint_text="e.g., 150")
        ticket_order_options = [ft.dropdown.Option(order, order.capitalize()) for order in [REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER]]
        ticket_order_dropdown = ft.Dropdown(label="Ticket Order", options=ticket_order_options, value=REVERSE_TICKET_ORDER, border_radius=8)
        game_number_field = NumberDecimalField(label="Game No.", is_integer_only=True, border_radius=8, on_submit=_save_new_game, hint_text="e.g., 453")
        error_text_add = ft.Text(visible=False, color=ft.Colors.RED_700)

        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Add New Game"),
            content=ft.Container(
                ft.Column(
                    [
                        game_name_field,
                        price_field,
                        total_tickets_field,
                        ticket_order_dropdown,
                        game_number_field,
                        error_text_add
                    ],
                    tight=True,
                    spacing=15,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=ft.padding.symmetric(horizontal=24, vertical=20),
                border_radius=8,
                width=self.page.width / 3.5,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=self._close_dialog, style=ft.ButtonStyle(color=ft.Colors.BLUE_GREY)),
                ft.FilledButton("Create Game", on_click=_save_new_game),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(self.page.dialog)

    def _handle_table_data_change(self, total_games: int, active_games: int, expired_games: int):
        self.total_games = total_games
        self.active_games = active_games
        self.expired_games = expired_games
        self.page.update()

    def _close_dialog(self, e=None):
        if self.page.dialog:
            self.page.close(self.page.dialog)
            self.page.dialog = None
            self.page.update()