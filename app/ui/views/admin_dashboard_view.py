import flet as ft
from app.constants import LOGIN_ROUTE
from app.core.models import User

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
        welcome_message = "Welcome, Admin!"
        if self.current_user and self.current_user.username:
            welcome_message = f"Welcome, {self.current_user.username} (Admin)!"

        # This is the content that goes *below* the AppBar
        return ft.Container( # Main content container
            content=ft.Column(
                [
                    ft.Text(welcome_message, size=28, weight=ft.FontWeight.BOLD),
                    ft.Text("Manage users, books, and view reports.", size=16),
                    ft.Text(f"System License is currently {'ACTIVE' if self.license_status else 'INACTIVE'}.",
                            size=14, weight=ft.FontWeight.W_500,
                            color=ft.Colors.GREEN_700 if self.license_status else ft.Colors.RED_700),
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
        # self.page.appbar = None # Router will handle clearing page.appbar
        self.router.navigate_to(LOGIN_ROUTE)

