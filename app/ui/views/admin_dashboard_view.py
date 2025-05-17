import flet as ft
from app.constants import LOGIN_ROUTE
from app.core.models import User
from app.ui import router
from app.ui.components.widgets.function_button import create_nav_card_button


class AdminDashboardView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user: User, license_status: bool, **params):
        super().__init__(expand=True) # The container itself will hold the main content area
        self.page = page
        self.router = router
        self.current_user = current_user
        self.license_status = license_status # Store license status

        # Set the page's AppBar
        self.page.appbar = self._build_appbar()

        # The content of this container will be the body of the dashboard
        self.content = self._build_body()

    def _build_appbar(self):
        return ft.AppBar(
            title=ft.Text("Admin Dashboard"),
            bgcolor=ft.Colors.BLUE_700, # Kept original color
            color=ft.Colors.WHITE,      # Kept original color
            actions=[
                ft.Text(f"Current User: {self.current_user.username}", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Container(width=20),
                ft.Text(f"License: {'Active' if self.license_status else 'Inactive'}", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Container(width=20), # Spacer
                ft.IconButton(
                    icon=ft.Icons.LOGOUT,
                    tooltip="Logout",
                    icon_color=ft.Colors.WHITE, # Kept original color
                    on_click=self.logout,
                ),
            ],
        )

    def _build_body(self):
        functions_section = ft.Container(
            ft.Column(
                controls=[
                    ft.Text("Sale Functions", weight=ft.FontWeight.BOLD, size=20),
                    ft.Row(
                        controls=[
                            create_nav_card_button(
                                router=router,
                                text="Sales Entry",
                                icon_name=ft.Icons.ATTACH_MONEY_ROUNDED,
                                accent_color=ft.Colors.TEAL_ACCENT_700,
                                navigate_to_route=LOGIN_ROUTE,
                                tooltip="Add Daily Sales",
                            ),
                            create_nav_card_button(
                                router=router,
                                text="Book Sale",
                                icon_name=ft.Icons.BOOK_OUTLINED,
                                accent_color=ft.Colors.BLUE_ACCENT_700,
                                navigate_to_route=LOGIN_ROUTE,
                                tooltip="Add Book Sale",
                            ),
                            create_nav_card_button(
                                router=router,
                                text="Open Book",
                                icon_name=ft.Icons.COLLECTIONS_BOOKMARK_OUTLINED,
                                accent_color=ft.Colors.GREEN_ACCENT_700,
                                navigate_to_route=LOGIN_ROUTE,
                                tooltip="Open Book"
                            ),
                        ],
                    ),
                    ft.Container(
                        height=20,
                    ),
                    ft.Text("Inventory Functions", weight=ft.FontWeight.BOLD, size=20),
                    ft.Row(
                        controls=[
                            create_nav_card_button(
                                router=router,
                                text="Add Game",
                                icon_name=ft.Icons.COLLECTIONS_BOOKMARK_OUTLINED,
                                accent_color=ft.Colors.GREEN_ACCENT_700,
                                navigate_to_route=LOGIN_ROUTE,
                                tooltip="Add New Game"
                            ),
                            create_nav_card_button(
                                router=router,
                                text="Manage Games",
                                icon_name=ft.Icons.MODE_EDIT_ROUNDED,
                                accent_color=ft.Colors.TEAL_ACCENT_700,
                                navigate_to_route=LOGIN_ROUTE,
                                tooltip="Manage Games Info"
                            ),

                            create_nav_card_button(
                                router=router,
                                text="Expire Game",
                                icon_name=ft.Icons.REMOVE_CIRCLE_OUTLINE,
                                accent_color=ft.Colors.RED_ACCENT_700,
                                navigate_to_route=LOGIN_ROUTE,
                                tooltip="Expire Game"
                            ),
                            create_nav_card_button(
                                router=router,
                                text="Add Books",
                                icon_name=ft.Icons.ADD_CIRCLE_OUTLINE,
                                accent_color=ft.Colors.GREEN_ACCENT_700,
                                navigate_to_route=LOGIN_ROUTE,
                                tooltip="Add Books"
                            ),
                            create_nav_card_button(
                                router=router,
                                text="Remove Books",
                                icon_name=ft.Icons.REMOVE_CIRCLE_OUTLINE,
                                accent_color=ft.Colors.RED_ACCENT_700,
                                navigate_to_route=LOGIN_ROUTE,
                                tooltip="Remove Books"
                            ),
                        ],
                    ),
                    ft.Container(
                        height=20,
                    ),
                    ft.Text("Report Functions", weight=ft.FontWeight.BOLD, size=20),
                    ft.Row(
                        controls=[
                            create_nav_card_button(
                                router=router,
                                text="Sales by Date",
                                icon_name=ft.Icons.EVENT_NOTE_OUTLINED,
                                accent_color=ft.Colors.GREEN_ACCENT_700,
                                navigate_to_route=LOGIN_ROUTE,
                                tooltip="Sales Report"
                            ),
                            create_nav_card_button(
                                router=router,
                                text="Book Open by Date",
                                icon_name=ft.Icons.BOOK_OUTLINED,
                                accent_color=ft.Colors.BLUE_ACCENT_700,
                                navigate_to_route=LOGIN_ROUTE,
                                tooltip="Book Open Report"
                            ),
                            create_nav_card_button(
                                router=router,
                                text="Game Expire by Date",
                                icon_name=ft.Icons.REMOVE_CIRCLE_OUTLINE,
                                accent_color=ft.Colors.RED_ACCENT_700,
                                navigate_to_route=LOGIN_ROUTE,
                                tooltip="Book Expire Report"
                            ),
                            create_nav_card_button(
                                router=router,
                                text="Book Stock by Date",
                                icon_name=ft.Icons.MODE_EDIT_ROUNDED,
                                accent_color=ft.Colors.INDIGO_ACCENT_700,
                                navigate_to_route=LOGIN_ROUTE,
                                tooltip="Book Stock Report"
                            ),
                        ],
                    ),
                    ft.Container(
                        height=20,
                    ),
                    ft.Text("Management Functions", weight=ft.FontWeight.BOLD, size=20),
                    ft.Row(
                        controls=[
                            create_nav_card_button(
                                router=router,
                                text="Add User",
                                icon_name=ft.Icons.ADD_CIRCLE_OUTLINE_OUTLINED,
                                accent_color=ft.Colors.GREEN_ACCENT_700,
                                navigate_to_route=LOGIN_ROUTE,
                                tooltip="Add User"
                            ),
                            create_nav_card_button(
                                router=router,
                                text="Manage Users",
                                icon_name=ft.Icons.MANAGE_ACCOUNTS_OUTLINED,
                                accent_color=ft.Colors.BLUE_ACCENT_700,
                                navigate_to_route=LOGIN_ROUTE,
                                tooltip="Manage Users"
                            ),
                            create_nav_card_button(
                                router=router,
                                text="Backup Database",
                                icon_name=ft.Icons.BACKUP_OUTLINED,
                                accent_color=ft.Colors.BLUE_ACCENT_700,
                                navigate_to_route=LOGIN_ROUTE,
                                tooltip="Backup Database"
                            ),
                        ],
                    ),
                ],
            ),
            expand=1,
        )

        # This is the content that goes *below* the AppBar
        return ft.Column(
            [
                functions_section,
            ],
            spacing=20, # Spacing between major sections
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER, # Stretch cards to fill width
            scroll=ft.ScrollMode.ADAPTIVE, # Add scroll if content overflows
            width=self.page.width / 2.5,
        )

    def logout(self, e):
        self.current_user = None
        # self.page.appbar = None # Router will handle clearing page.appbar
        self.router.navigate_to(LOGIN_ROUTE)

