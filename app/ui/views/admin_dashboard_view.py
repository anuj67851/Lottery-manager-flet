import flet as ft
from app.constants import LOGIN_ROUTE, GAME_MANAGEMENT_ROUTE, ADMIN_DASHBOARD_ROUTE, BOOK_MANAGEMENT_ROUTE
from app.core.models import User
from app.ui.components.widgets.function_button import create_nav_card_button
from app.ui.components.common.appbar_factory import create_appbar # Import AppBar factory

class AdminDashboardView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user: User, license_status: bool, **params):
        super().__init__(expand=True)
        self.page = page
        self.router = router
        self.current_user = current_user
        self.license_status = license_status

        # Navigation parameters for child views, allowing them to return here
        self.navigation_params_for_children = {
            "current_user": self.current_user,
            "license_status": self.license_status,
            "previous_view_route": ADMIN_DASHBOARD_ROUTE, # This view's route
            "previous_view_params": { # Params needed to reconstruct this view if returned to
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
        """Helper to create a styled, scrollable container for a function section (quadrant)."""
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
                    wrap=True, # Allow buttons to wrap if quadrant is too narrow
                ),
            ],
            spacing=15,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.ADAPTIVE, # Enable scrolling for content overflow
            # Do not set expand=True here for scrollable_content
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
            expand=True, # Quadrant container expands to fill its grid cell
            alignment=ft.alignment.center, # Center the scrollable content within
        )
        return quadrant_container

    def _build_sales_functions_quadrant(self) -> ft.Container:
        buttons = [
            create_nav_card_button(
                router=self.router, text="Sales Entry", icon_name=ft.Icons.POINT_OF_SALE_ROUNDED,
                accent_color=ft.Colors.GREEN_700, navigate_to_route=LOGIN_ROUTE, tooltip="Add Daily Sales", disabled=True), # Example disabled
            create_nav_card_button(
                router=self.router, text="Book Sale", icon_name=ft.Icons.BOOK_ONLINE_ROUNDED,
                accent_color=ft.Colors.BLUE_700, navigate_to_route=LOGIN_ROUTE, tooltip="Add Book Sale", disabled=True),
            create_nav_card_button(
                router=self.router, text="Open Book", icon_name=ft.Icons.AUTO_STORIES_ROUNDED,
                accent_color=ft.Colors.TEAL_700, navigate_to_route=LOGIN_ROUTE, tooltip="Open Book", disabled=True),
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
                accent_color=ft.Colors.BROWN_600, navigate_to_route=BOOK_MANAGEMENT_ROUTE, # Placeholder, assuming BOOK_MANAGEMENT_ROUTE
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
                accent_color=ft.Colors.ORANGE_700, navigate_to_route=LOGIN_ROUTE, tooltip="Sales Report", disabled=True),
            create_nav_card_button(
                router=self.router, text="Book Open Report", icon_name=ft.Icons.ASSESSMENT_ROUNDED,
                accent_color=ft.Colors.INDIGO_400, navigate_to_route=LOGIN_ROUTE, tooltip="Book Open Report", disabled=True),
            create_nav_card_button(
                router=self.router, text="Game Expiry Report", icon_name=ft.Icons.UPDATE_ROUNDED,
                accent_color=ft.Colors.DEEP_ORANGE_700, navigate_to_route=LOGIN_ROUTE, tooltip="Game Expire Report", disabled=True),
            create_nav_card_button(
                router=self.router, text="Stock Levels", icon_name=ft.Icons.STACKED_BAR_CHART_ROUNDED,
                accent_color=ft.Colors.BROWN_500, navigate_to_route=LOGIN_ROUTE, tooltip="Book Stock Report", disabled=True),
        ]
        return self._create_section_quadrant(
            title="Data & Reports", title_color=ft.Colors.AMBER_900,
            button_row_controls=buttons,
            gradient_colors=[ft.Colors.AMBER_50, ft.Colors.YELLOW_100]
        )

    def _build_management_functions_quadrant(self) -> ft.Container:
        buttons = [
            create_nav_card_button(
                router=self.router, text="Manage Users", icon_name=ft.Icons.MANAGE_ACCOUNTS_ROUNDED,
                accent_color=ft.Colors.INDIGO_700, navigate_to_route=LOGIN_ROUTE, tooltip="Manage Users", disabled=True), # Assuming a route for user management
            create_nav_card_button(
                router=self.router, text="Backup Database", icon_name=ft.Icons.SETTINGS_BACKUP_RESTORE_ROUNDED,
                accent_color=ft.Colors.BLUE_800, navigate_to_route=LOGIN_ROUTE, tooltip="Backup Database", disabled=True),
        ]
        return self._create_section_quadrant(
            title="System Management", title_color=ft.Colors.DEEP_PURPLE_800,
            button_row_controls=buttons,
            gradient_colors=[ft.Colors.DEEP_PURPLE_50, ft.Colors.INDIGO_100]
        )

    def _build_body(self) -> ft.Column:
        divider_color = ft.Colors.with_opacity(0.3, ft.Colors.ON_SURFACE)
        divider_thickness = 2

        # Create a responsive grid for the quadrants
        # On larger screens, it could be 2x2. On smaller, 1xN.
        # For simplicity with Flet's Row/Column, we'll keep 2x2 for now.
        # Flet's ResponsiveRow could be used for more complex responsive layouts.

        main_content_area = ft.GridView(
            runs_count=2, # Try to fit 2 items per row (effectively 2 columns if items are wide enough)
            max_extent=self.page.width / 2.2 if self.page.width else 400, # Max width of each child
            child_aspect_ratio=1.0, # Adjust for desired height relative to width
            spacing=10,
            run_spacing=10,
            expand=True, # GridView expands
            controls=[ # Quadrants will try to fit based on max_extent
                self._build_sales_functions_quadrant(),
                self._build_inventory_functions_quadrant(),
                self._build_report_functions_quadrant(),
                self._build_management_functions_quadrant(),
            ],
        )
        # Fallback to Column layout if GridView doesn't provide desired control or for simplicity:
        row1 = ft.Row(
            controls=[
                self._build_sales_functions_quadrant(),
                # ft.VerticalDivider(width=divider_thickness, thickness=divider_thickness, color=divider_color),
                self._build_inventory_functions_quadrant(),
            ],
            spacing=10, expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH
        )
        row2 = ft.Row(
            controls=[
                self._build_report_functions_quadrant(),
                # ft.VerticalDivider(width=divider_thickness, thickness=divider_thickness, color=divider_color),
                self._build_management_functions_quadrant(),
            ],
            spacing=10, expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH
        )

        return ft.Column(
            controls=[row1, ft.Divider(height=divider_thickness, thickness=divider_thickness, color=divider_color), row2],
            spacing=10, expand=True,
        )