import flet as ft
from app.constants import LOGIN_ROUTE, SALESPERSON_ROLE, ADMIN_ROLE, EMPLOYEE_ROLE
from app.core.models import User
from app.ui.components.tables.users_table import UsersTable


class SalesPersonDashboardView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user: User = None, **params):
        super().__init__(expand=True)
        self.page = page
        self.router = router
        self.current_user = current_user

        self.users_table = UsersTable(self.page, user_roles=[SALESPERSON_ROLE, ADMIN_ROLE, EMPLOYEE_ROLE])

        # Set the page's AppBar
        self.page.appbar = self._build_appbar()

        # The content of this container will be the body of the dashboard
        self.content = self._build_body()

    def _build_appbar(self):
        return ft.AppBar(
            title=ft.Text("Sales person Dashboard"),
            bgcolor=ft.Colors.BLUE_700,
            color=ft.Colors.WHITE,
            actions=[
                ft.IconButton(
                    icon=ft.Icons.LOGOUT,
                    tooltip="Logout",
                    icon_color=ft.Colors.WHITE,
                    on_click=self.logout,
                ),
            ],
        )

    def _build_body(self):
        welcome_message = "Welcome, Sales person!"
        if self.current_user and self.current_user.username:
            welcome_message = f"Welcome, {self.current_user.username} (Sales Person)!"

        return ft.Container(  # Main content container
            content=ft.Column( # column containing welcome message and content
                [
                    ft.Text(welcome_message, size=28, weight=ft.FontWeight.BOLD),
                    ft.Row( # row for key and users
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text("Activate / Deactivate License"),
                                    ft.Button(
                                        icon=ft.Icons.KEY,
                                        text="Activate License",
                                        on_click=lambda e: print("Activate license"),
                                    ),
                                ]
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text("Manage Users"),
                                    self.users_table,
                                ]
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.START,
                spacing=20,
            ),
            padding=50,
            alignment=ft.alignment.center,
            expand=True
        )

    def logout(self, e):
        self.current_user = None
        self.page.appbar = None  # Clear the appbar when logging out
        self.router.navigate_to(LOGIN_ROUTE)
