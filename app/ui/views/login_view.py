"""
Login view for the application.

This module provides a Flet view for the login page.
"""
import flet as ft

from app.ui.components.login_form import LoginForm
from app.ui.components.admin_creation_form import AdminCreationForm
from app.data.crud_users import any_users_exist
from app.data.database import get_db_session

class LoginView(ft.Container):
    """
    A view component for the login page.
    """

    def __init__(self, page: ft.Page, router, **params):
        """
        Initialize the login view.

        Args:
            page (ft.Page): The Flet page.
            router: The router for navigation.
            **params: Additional parameters.
        """
        super().__init__()
        self.page = page
        self.router = router

        # Set page properties
        self.page.title = "Login - Lottery Manager"
        self.page.vertical_alignment = ft.MainAxisAlignment.CENTER
        self.page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        # Check if any users exist
        with get_db_session() as db:
            users_exist = any_users_exist(db)
            # Create appropriate form
            if users_exist:
                # Create login form
                self.current_form = LoginForm(on_login_success=self.on_login_success)
            else:
                # Create admin creation form
                self.current_form = AdminCreationForm(on_admin_created=self.on_admin_created)

    def build(self):
        """
        Build the login view.

        Returns:
            ft.Control: The built view.
        """
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Icon(
                            ft.Icons.VERIFIED_USER,
                            color=ft.Colors.BLUE,
                            size=100,
                        ),
                        visible=False,  # Set to True if logo is available
                    ),
                    ft.Container(
                        content=self.current_form,
                        padding=20,
                        border_radius=10,
                        bgcolor=ft.Colors.WHITE,
                        shadow=ft.BoxShadow(
                            spread_radius=1,
                            blur_radius=15,
                            color=ft.Colors.BLACK12,
                        ),
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=20,
            ),
            padding=50,
            alignment=ft.alignment.center,
        )

    def on_login_success(self, role: str):
        """
        Handle successful login.

        Args:
            role (str): The role of the authenticated user.
        """
        # Navigate to appropriate dashboard based on user role
        if role == "admin":
            self.router.navigate_to("admin_dashboard")
        else:
            self.router.navigate_to("employee_dashboard")

    def on_admin_created(self):
        """
        Handle successful admin creation.

        This method is called when the admin user is successfully created.
        It reloads the login view to show the login form.
        """
        # Reload the login view
        self.router.navigate_to("login")
