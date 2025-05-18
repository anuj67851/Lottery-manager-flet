import threading

import flet as ft

from app.constants import LOGIN_ROUTE, ADMIN_DASHBOARD_ROUTE, \
    REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER
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
        super().__init__(expand=True, padding=20) # Added padding to main container
        self.game_service = GameService()
        self.page = page
        self.router = router
        self.current_user = current_user
        self.license_status = license_status

        self.total_games_widget = ft.Text("", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD)
        self.active_games_widget = ft.Text("", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD)
        self.expired_games_widget = ft.Text("", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD)

        self.previous_view_route = previous_view_route
        self.previous_view_params = previous_view_params if previous_view_params is not None else {}

        self.games_table_component = GamesTable(
            page=self.page,
            on_data_changed=self._handle_table_data_change,
            game_service=self.game_service
        )
        self.games_table_component._last_search_term = "" # Initialize search term tracking

        self.search_field = ft.TextField(
            label="Search Games (Name, Number, Price, Number of Tickets)",
            hint_text="Type to search...",
            on_change=self._on_search_change, # Use debounce for on_change
            prefix_icon=ft.Icons.SEARCH,
            border_radius=8,
            expand=True, # Let it expand
        )
        self._debounce_timer = None # For search debounce

        self.page.appbar = self._build_appbar()
        self.content = self._build_body()
        # Initial data load (will also update stats via on_data_changed)
        self.games_table_component.refresh_data()

    def _on_search_change(self, e: ft.ControlEvent):
        # Simple debounce: if user types quickly, only search after they pause
        if self._debounce_timer:
            self._debounce_timer.cancel() # Cancel previous timer

        # Define what to do after the debounce period
        def debounced_search():
            search_term = e.control.value
            self.games_table_component._last_search_term = search_term # Store for actions
            self.games_table_component.filter_and_sort_games(search_term)
            # Stats update is handled by on_data_changed if we refresh all data,
            # but if we only filter, we might need to update stats manually or adjust on_data_changed.
            # For now, filter_and_sort_games doesn't re-fetch, so stats remain global.

        # Start a new timer
        self._debounce_timer = threading.Timer(0.5, debounced_search) # 0.5 seconds delay
        self._debounce_timer.start()


    def logout(self, e):
        self.current_user = None
        self.router.navigate_to(LOGIN_ROUTE)

    def _go_back(self, e):
        self.router.navigate_to(self.previous_view_route, **self.previous_view_params)

    def _build_appbar(self):
        return ft.AppBar(
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                tooltip="Go Back",
                icon_color=ft.Colors.WHITE,
                on_click=self._go_back,
            ),
            leading_width=70,
            title=ft.Text("Admin Dashboard > Game Management"),
            bgcolor=ft.Colors.BLUE_700,
            color=ft.Colors.WHITE,
            actions=[
                ft.Text(f"User: {self.current_user.username}", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Container(width=10),
                ft.Text(f"License: {'Active' if self.license_status else 'Inactive'}", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Container(width=10),
                ft.IconButton(icon=ft.Icons.LOGOUT, tooltip="Logout", icon_color=ft.Colors.WHITE, on_click=self.logout),
            ],
        )

    def _build_body(self):
        stats_and_actions_row = ft.Row(
            controls=[
                self.total_games_widget,
                self.active_games_widget,
                self.expired_games_widget,
                ft.Container(expand=True), # Spacer
                ft.FilledButton(
                    "Add New Game",
                    icon=ft.Icons.GAMEPAD_OUTLINED,
                    on_click=self._handle_add_game_click,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20, # Add some spacing between stats
        )

        search_row = ft.Row(
            [self.search_field],
            alignment=ft.MainAxisAlignment.START
        )

        game_management_section = ft.Card(
            elevation=4,
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text( # Main Title for the section
                            "Game Configuration & Overview",
                            style=ft.TextThemeStyle.HEADLINE_SMALL, # Made header larger
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER
                        ),
                        ft.Divider(),
                        stats_and_actions_row,
                        ft.Divider(height=5, color=ft.Colors.TRANSPARENT),
                        search_row, # Search bar added here
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        self.games_table_component,
                    ],
                    spacing=15,
                ),
                padding=20,
                border_radius=8,
                expand=True,
                bgcolor=ft.Colors.WHITE70, # Adjusted for better theme consistency
            ),
            expand=True
        )
        return ft.Column(
            [
                game_management_section,
            ],
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH, # Stretch card
            scroll=ft.ScrollMode.ADAPTIVE,
        )

    def _handle_add_game_click(self, e):
        self._open_add_game_dialog()

    def _open_add_game_dialog(self):
        game_name_field = ft.TextField(label="Game Name", autofocus=True, border_radius=8)
        price_field = NumberDecimalField(
            label="Price (e.g., $1.00, $0.50)", # Example for float
            hint_text="e.g., 1.00 or 0.50",
            is_money_field=True,
            currency_symbol="$",
            is_integer_only=False, # Allow decimals
        )
        total_tickets_field = NumberDecimalField(label="Total Tickets", is_integer_only=True, border_radius=8, hint_text="e.g., 150")
        ticket_order_options = [ft.dropdown.Option(order, order.capitalize()) for order in [REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER]]
        ticket_order_dropdown = ft.Dropdown(label="Ticket Order", options=ticket_order_options, value=REVERSE_TICKET_ORDER, border_radius=8)
        game_number_field = NumberDecimalField(label="Game No.", is_integer_only=True, border_radius=8, hint_text="e.g., 453")
        error_text_add = ft.Text(visible=False, color=ft.Colors.RED_700)

        def _save_new_game(e): # Nested to capture dialog fields
            error_text_add.value = ""
            error_text_add.visible = False

            game_name = game_name_field.value.strip()
            # Get price as float, then multiply by 100 to store as cents (integer)
            price_float = price_field.get_value_as_float()
            price_cents = None
            if price_float is not None:
                price_cents = int(price_float * 100) # Convert to cents

            total_tickets = total_tickets_field.get_value_as_int()
            order = ticket_order_dropdown.value
            game_number = game_number_field.get_value_as_int()

            # Validation
            if not game_name:
                error_text_add.value = "Game Name is required."
            elif price_cents is None: # Check if price was valid and converted
                error_text_add.value = "Valid Price is required (e.g., 1.00, 0.50)."
            elif total_tickets is None or total_tickets <= 0:
                error_text_add.value = "Total Tickets must be a positive number."
            elif not order:
                error_text_add.value = "Ticket Order is required."
            elif game_number is None or game_number <=0:
                error_text_add.value = "Game Number must be a positive number."

            if error_text_add.value: # If any error was set
                error_text_add.visible = True
                if error_text_add.page: error_text_add.update()
                if self.page: self.page.update() # Update dialog
                return

            try:
                with get_db_session() as db:
                    # Pass price_cents to your service/crud layer
                    # Assuming your create_game expects price in cents or original unit.
                    # If it expects float, pass price_float.
                    # For this example, let's assume it expects cents.
                    self.game_service.create_game(db, game_name, price_cents, total_tickets, game_number, order)
                self.page.open(ft.SnackBar(ft.Text(f"Game '{game_number} -- {game_name}' created successfully!"), open=True))
                self._close_dialog()
                self.games_table_component.refresh_data(self.search_field.value) # Refresh table with current search
            except (ValidationError, DatabaseError) as ex:
                error_text_add.value = str(ex)
                error_text_add.visible = True
            except Exception as ex_general:
                error_text_add.value = f"An unexpected error occurred: {ex_general}"
                error_text_add.visible = True

            if error_text_add.page: error_text_add.update()
            if self.page: self.page.update() # Update dialog if error

        # Rebuild dialog content and actions using the local _save_new_game
        dialog_content = ft.Container(
            ft.Column(
                [
                    game_name_field, price_field, total_tickets_field,
                    ticket_order_dropdown, game_number_field, error_text_add
                ],
                tight=True, spacing=15, scroll=ft.ScrollMode.AUTO,
            ),
            padding=ft.padding.symmetric(horizontal=24, vertical=20),
            border_radius=8,
            width= (self.page.width / 3.5) if self.page.width else 400, # ensure page.width is available
        )
        dialog_actions = [
            ft.TextButton("Cancel", on_click=self._close_dialog, style=ft.ButtonStyle(color=ft.Colors.BLUE_GREY)),
            ft.FilledButton("Create Game", on_click=_save_new_game),
        ]

        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Add New Game"),
            content=dialog_content,
            actions=dialog_actions,
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(self.page.dialog)


    def _handle_table_data_change(self, total_games: int, active_games: int, expired_games: int):
        # This callback now receives stats for ALL games, not just filtered ones
        self.total_games_widget.value = f"Total Games: {total_games}"
        self.active_games_widget.value = f"Active Games: {active_games}"
        self.expired_games_widget.value = f"Expired Games: {expired_games}"
        if self.page: self.page.update() # Update the part of the page showing these stats

    def _close_dialog(self, e=None):
        if self.page.dialog:
            self.page.close(self.page.dialog)
            self.page.dialog = None
            if self.page: self.page.update()