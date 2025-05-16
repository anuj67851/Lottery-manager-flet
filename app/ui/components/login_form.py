import flet as ft
from typing import Callable

from app.core.auth_service import AuthService
from app.data.database import get_db_session
from app.core.exceptions import AuthenticationError, ValidationError

class LoginForm(ft.Container):
    def __init__(self, page: ft.Page, on_login_success: Callable[[str], None]): # Added page parameter
        super().__init__(padding=10, border_radius=10)
        self.page = page # Store the page reference
        self.on_login_success = on_login_success

        self.username_field = ft.TextField(
            label="Username",
            autofocus=True,
            width=300,
        )
        self.password_field = ft.TextField(
            label="Password",
            password=True,
            can_reveal_password=True,
            width=300,
        )
        self.error_text = ft.Text(
            color=ft.Colors.RED,
            visible=False,
        )
        self.login_button = ft.ElevatedButton(
            text="Login",
            width=300,
            on_click=self.login_clicked,
        )
        self.content = self._build_layout()

    def _build_layout(self):
        return ft.Column(
            controls=[
                ft.Text("Login", size=30, weight=ft.FontWeight.BOLD),
                ft.Text("Please enter your credentials", size=16),
                ft.Container(height=20),
                self.username_field,
                self.password_field,
                self.error_text,
                ft.Container(height=10),
                self.login_button,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        )

    def login_clicked(self, e):
        # 1. Clear previous error and update only the error text control
        self.error_text.value = ""
        self.error_text.visible = False
        self.error_text.update() # Update specific control

        # 2. Get username and password
        username = self.username_field.value
        password = self.password_field.value

        # 3. Authenticate user
        try:
            with get_db_session() as db:
                user = AuthService.authenticate_user(db, username, password)
            # If successful, the on_login_success callback will handle navigation
            # and the router will update the page.
            self.on_login_success(user)
        except (AuthenticationError, ValidationError) as ex:
            self.error_text.value = ex.message
            self.error_text.visible = True
            self.error_text.update() # Update specific control
        except Exception as ex_general: # Catch any other unexpected errors
            print(f"Unexpected error in login: {ex_general}") # For debugging
            self.error_text.value = "An unexpected error occurred during login."
            self.error_text.visible = True
            self.error_text.update() # Update specific control