import flet as ft
from app.core.models import User
from app.ui.components.common.appbar_factory import create_appbar # Import AppBar factory

class EmployeeDashboardView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user: User, license_status: bool, **params):
        super().__init__(expand=True)
        self.page = page
        self.router = router
        self.current_user = current_user
        self.license_status = license_status

        self.page.appbar = create_appbar(
            page=self.page,
            router=self.router,
            title_text="Employee Dashboard",
            current_user=self.current_user, # Show current user
            license_status=self.license_status,
            show_user_info=True # Explicitly show user info
        )
        self.content = self._build_body()

    def _build_body(self) -> ft.Container:
        welcome_message = "Welcome, Employee!"
        if self.current_user and self.current_user.username:
            welcome_message = f"Welcome, {self.current_user.username}!"

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(welcome_message, size=28, weight=ft.FontWeight.BOLD),
                    ft.Text("This is the Employee Dashboard. Functionality to be added.", size=16),
                    # Add employee-specific functions/buttons here
                    # e.g., ft.FilledButton("Enter Daily Sales", on_click=lambda e: print("Sales Entry Clicked"))
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=20,
            ),
            padding=50,
            alignment=ft.alignment.center,
            expand=True
        )