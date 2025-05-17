import flet as ft
from typing import Callable

from sqlalchemy.orm.exc import DetachedInstanceError

from app.services.auth_service import AuthService # Use AuthService
from app.data.database import get_db_session
from app.core.exceptions import AuthenticationError, ValidationError
from app.core.models import User

class LoginForm(ft.Container):
    def __init__(self, page: ft.Page, on_login_success: Callable[[User], None]):
        super().__init__()
        self.page = page
        self.on_login_success = on_login_success
        self.auth_service = AuthService() # Instantiate AuthService

        self.username_field = ft.TextField(
            label="Username",
            autofocus=True,
            expand=True, # Make field expand to container width
            border_radius=8,
            prefix_icon=ft.Icons.PERSON_OUTLINE_ROUNDED,
            content_padding=ft.padding.symmetric(vertical=14, horizontal=12), # Slightly more padding
            on_submit=self.login_clicked,
        )
        self.password_field = ft.TextField(
            label="Password",
            password=True,
            can_reveal_password=True,
            expand=True,
            border_radius=8,
            prefix_icon=ft.Icons.LOCK_OUTLINE_ROUNDED,
            on_submit=self.login_clicked,
            content_padding=ft.padding.symmetric(vertical=14, horizontal=12)
        )
        self.error_text = ft.Text(
            visible=False,
            weight=ft.FontWeight.W_500,
            color=ft.Colors.RED_700
        )
        self.login_button = ft.FilledButton(
            text="Login",
            expand=True,
            height=48, # Taller button
            on_click=self.login_clicked,
            icon=ft.Icons.LOGIN_ROUNDED
        )
        self.content = self._build_layout()

    def _build_layout(self):
        return ft.Column(
            controls=[
                ft.Text(
                    "Welcome Back!",
                    style=ft.TextThemeStyle.HEADLINE_SMALL, # Using theme style
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(
                    "Sign in to access your account.",
                    style=ft.TextThemeStyle.BODY_LARGE,
                    color=ft.Colors.ON_SURFACE_VARIANT, # Softer color
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=20), # Spacing
                self.username_field,
                self.password_field,
                self.error_text,
                ft.Container(height=15), # Spacing
                self.login_button,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH, # Stretch fields/button
            spacing=12, # Spacing between form elements
        )

    def login_clicked(self, e=None):
        self.error_text.value = ""
        self.error_text.visible = False

        username = self.username_field.value.strip()
        password = self.password_field.value

        try:
            with get_db_session() as db:
                user_obj = self.auth_service.authenticate_user(db, username, password)

                # making copy since the object above will be detached after login
                user_data = User(id=user_obj.id, username=user_obj.username, role=user_obj.role)
            self.on_login_success(user_data)
        except (AuthenticationError, ValidationError) as ex:
            self.error_text.value = ex.message
            self.error_text.visible = True
        except DetachedInstanceError as di_err:
            print(f"SQLAlchemy DetachedInstanceError during/after login success: {di_err}")
            self.error_text.value = "Login successful, but a session error occurred. Please try again or contact support."
            self.error_text.visible = True
        except Exception as ex_general:
            print(f"Unexpected error in login: {ex_general}")
            self.error_text.value = "An unexpected error occurred during login."
            self.error_text.visible = True

        if self.page: self.page.update()