import flet as ft
from app.constants import LOGIN_ROUTE
from app.core.models import User

class SalesPersonDashboardView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user: User = None, **params):
        super().__init__(expand=True)
        self.page = page
        self.router = router
        self.current_user = current_user

        # Set the page's AppBar
        self.page.appbar = self._build_appbar()

        # The content of this container will be the body of the dashboard
        self.content = self._build_body()
        # self.page.update()

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
            welcome_message = f"Welcome, {self.current_user.username}!"

        # This is the content that goes *below* the AppBar
        return ft.Container( # Main content container
            content=ft.Column(
                [
                    ft.Text(welcome_message, size=28, weight=ft.FontWeight.BOLD),
                    ft.Text("Manage Users and License", size=16),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=20,
            ),
            padding=50,
            alignment=ft.alignment.center,
            expand=True
        )

    def logout(self, e):
        self.current_user = None
        self.page.appbar = None # Clear the appbar when logging out
        self.router.navigate_to(LOGIN_ROUTE)