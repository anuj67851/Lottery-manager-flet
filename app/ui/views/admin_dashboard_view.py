import flet as ft
from app.constants import LOGIN_ROUTE
from app.core.models import User
from app.ui.components.widgets.function_button import create_nav_card_button


class AdminDashboardView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user: User, license_status: bool, **params):
        super().__init__(expand=True)
        self.page = page
        self.router = router
        self.current_user = current_user
        self.license_status = license_status

        self.page.appbar = self._build_appbar()  # Reverted AppBar build
        self.content = self._build_body()

    def _build_appbar(self):
        # Reverted to the original AppBar structure and styling
        return ft.AppBar(
            title=ft.Text("Admin Dashboard"),
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
                    icon=ft.Icons.LOGOUT,  # Original icon
                    tooltip="Logout",
                    icon_color=ft.Colors.WHITE,
                    on_click=self.logout,
                ),
            ],
        )

    def _create_section_quadrant(self, title: str, title_color: str,
                                 button_row_controls: list, gradient_colors: list) -> ft.Container:
        """Helper to create a styled, scrollable container for a function section (quadrant)."""

        # This inner Column contains the actual content (title, buttons) and will be scrollable.
        # It does NOT expand itself; its size is determined by its content.
        # If content is larger than the quadrant's allocated space, it scrolls.
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
                    spacing=10,  # Original spacing
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    wrap=True,
                ),
            ],
            spacing=15,  # Original spacing
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            # Key change for scrollability:
            scroll=ft.ScrollMode.ADAPTIVE,
            # Do not set expand=True here, let the parent container manage expansion
        )

        # This is the main container for the quadrant that fills its grid cell
        quadrant_container = ft.Container(
            content=scrollable_content,  # The scrollable content goes here
            padding=15,  # Original padding
            border_radius=10,  # Original radius
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,  # Original gradient direction
                end=ft.alignment.bottom_right,
                colors=gradient_colors,  # New gradient colors
            ),
            expand=True,  # Crucial: The quadrant container expands to fill its cell
            alignment=ft.alignment.center,  # Centers the (potentially smaller) scrollable_content
        )
        return quadrant_container

    # Using the improved color schemes for quadrants, titles, and button accents from previous good suggestion
    def _build_sales_functions_quadrant(self) -> ft.Container:
        buttons = [
            create_nav_card_button(
                router=self.router, text="Sales Entry", icon_name=ft.Icons.POINT_OF_SALE_ROUNDED,  # Updated Icon
                accent_color=ft.Colors.GREEN_700, navigate_to_route=LOGIN_ROUTE, tooltip="Add Daily Sales"),
            create_nav_card_button(
                router=self.router, text="Book Sale", icon_name=ft.Icons.BOOK_ONLINE_ROUNDED,  # Updated Icon
                accent_color=ft.Colors.BLUE_700, navigate_to_route=LOGIN_ROUTE, tooltip="Add Book Sale"),
            create_nav_card_button(
                router=self.router, text="Open Book", icon_name=ft.Icons.AUTO_STORIES_ROUNDED,  # Updated Icon
                accent_color=ft.Colors.TEAL_700, navigate_to_route=LOGIN_ROUTE, tooltip="Open Book"),
        ]
        return self._create_section_quadrant(
            title="Sale Functions", title_color=ft.Colors.CYAN_900,  # New title color
            button_row_controls=buttons,
            gradient_colors=[ft.Colors.CYAN_50, ft.Colors.LIGHT_BLUE_100]  # New gradient
        )

    def _build_inventory_functions_quadrant(self) -> ft.Container:
        buttons = [
            create_nav_card_button(
                router=self.router, text="Add Game", icon_name=ft.Icons.ADD_BUSINESS_ROUNDED,  # Updated Icon
                accent_color=ft.Colors.GREEN_800, navigate_to_route=LOGIN_ROUTE, tooltip="Add New Game"),
            create_nav_card_button(
                router=self.router, text="Manage Games", icon_name=ft.Icons.EDIT_NOTE_ROUNDED,  # Updated Icon
                accent_color=ft.Colors.BLUE_GREY_700, navigate_to_route=LOGIN_ROUTE, tooltip="Manage Games Info"),
            create_nav_card_button(
                router=self.router, text="Expire Game", icon_name=ft.Icons.EVENT_REPEAT_ROUNDED,  # Updated Icon
                accent_color=ft.Colors.ORANGE_800, navigate_to_route=LOGIN_ROUTE, tooltip="Expire Game"),
            create_nav_card_button(
                router=self.router, text="Add Books", icon_name=ft.Icons.LIBRARY_ADD_ROUNDED,  # Updated Icon
                accent_color=ft.Colors.LIME_800, navigate_to_route=LOGIN_ROUTE, tooltip="Add Books"),
            create_nav_card_button(
                router=self.router, text="Remove Books", icon_name=ft.Icons.DELETE_SWEEP_ROUNDED,  # Updated Icon
                accent_color=ft.Colors.RED_700, navigate_to_route=LOGIN_ROUTE, tooltip="Remove Books"),
        ]
        return self._create_section_quadrant(
            title="Inventory Control", title_color=ft.Colors.GREEN_900,  # New title color
            button_row_controls=buttons,
            gradient_colors=[ft.Colors.LIGHT_GREEN_50, ft.Colors.GREEN_100]  # New gradient
        )

    def _build_report_functions_quadrant(self) -> ft.Container:
        buttons = [
            create_nav_card_button(
                router=self.router, text="Sales by Date", icon_name=ft.Icons.CALENDAR_MONTH_ROUNDED,  # Updated Icon
                accent_color=ft.Colors.ORANGE_700, navigate_to_route=LOGIN_ROUTE, tooltip="Sales Report"),
            create_nav_card_button(
                router=self.router, text="Book Open Report", icon_name=ft.Icons.ASSESSMENT_ROUNDED,  # Updated Icon
                accent_color=ft.Colors.INDIGO_400, navigate_to_route=LOGIN_ROUTE, tooltip="Book Open Report"),
            create_nav_card_button(
                router=self.router, text="Game Expiry Report", icon_name=ft.Icons.UPDATE_ROUNDED,  # Updated Icon
                accent_color=ft.Colors.DEEP_ORANGE_700, navigate_to_route=LOGIN_ROUTE, tooltip="Game Expire Report"),
            create_nav_card_button(
                router=self.router, text="Stock Levels", icon_name=ft.Icons.STACKED_BAR_CHART_ROUNDED,  # Updated Icon
                accent_color=ft.Colors.BROWN_500, navigate_to_route=LOGIN_ROUTE, tooltip="Book Stock Report"),
        ]
        return self._create_section_quadrant(
            title="Data & Reports", title_color=ft.Colors.AMBER_900,  # New title color
            button_row_controls=buttons,
            gradient_colors=[ft.Colors.AMBER_50, ft.Colors.YELLOW_100]  # New gradient
        )

    def _build_management_functions_quadrant(self) -> ft.Container:
        buttons = [
            create_nav_card_button(
                router=self.router, text="Add User", icon_name=ft.Icons.PERSON_ADD_ROUNDED,  # Updated Icon
                accent_color=ft.Colors.TEAL_700, navigate_to_route=LOGIN_ROUTE, tooltip="Add User"),
            create_nav_card_button(
                router=self.router, text="Manage Users", icon_name=ft.Icons.MANAGE_ACCOUNTS_ROUNDED,  # Updated Icon
                accent_color=ft.Colors.INDIGO_700, navigate_to_route=LOGIN_ROUTE, tooltip="Manage Users"),
            create_nav_card_button(
                router=self.router, text="Backup Database", icon_name=ft.Icons.SETTINGS_BACKUP_RESTORE_ROUNDED,
                # Updated Icon
                accent_color=ft.Colors.BLUE_800, navigate_to_route=LOGIN_ROUTE, tooltip="Backup Database"),
        ]
        return self._create_section_quadrant(
            title="System Management", title_color=ft.Colors.DEEP_PURPLE_800,  # New title color
            button_row_controls=buttons,
            gradient_colors=[ft.Colors.DEEP_PURPLE_50, ft.Colors.INDIGO_100]  # New gradient
        )

    def _build_body(self):
        # Using the original divider style from the "perfect" version
        divider_color = ft.Colors.with_opacity(0.3, ft.Colors.ON_SURFACE)
        divider_thickness = 2

        row1 = ft.Row(
            controls=[
                self._build_sales_functions_quadrant(),
                ft.VerticalDivider(width=divider_thickness, thickness=divider_thickness, color=divider_color),
                self._build_inventory_functions_quadrant(),
            ],
            spacing=10,  # Original spacing
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH
        )

        row2 = ft.Row(
            controls=[
                self._build_report_functions_quadrant(),
                ft.VerticalDivider(width=divider_thickness, thickness=divider_thickness, color=divider_color),
                self._build_management_functions_quadrant(),
            ],
            spacing=10,  # Original spacing
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH
        )

        return ft.Column(
            controls=[
                row1,
                ft.Divider(height=divider_thickness, thickness=divider_thickness, color=divider_color),
                row2,
            ],
            spacing=10,  # Original spacing
            expand=True,
        )

    def logout(self, e):
        self.current_user = None
        self.router.navigate_to(LOGIN_ROUTE)
