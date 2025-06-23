import logging

import flet as ft
from typing import Callable, Optional

from sqlalchemy.orm.exc import DetachedInstanceError # Keep for specific error handling

from app.services.auth_service import AuthService # Use AuthService
from app.data.database import get_db_session
from app.core.exceptions import AuthenticationError, ValidationError
from app.core.models import User

logger = logging.getLogger("lottery_manager_app")

class LoginForm(ft.Container):
    def __init__(self, page: ft.Page, on_login_success: Callable[[User], None]):
        super().__init__() # Removed expand=True, let parent control expansion
        self.page = page
        self.on_login_success = on_login_success
        self.auth_service = AuthService()

        self.username_field = ft.TextField(
            label="Username",
            autofocus=True,
            expand=True,
            border_radius=8,
            prefix_icon=ft.Icons.PERSON_OUTLINE_ROUNDED,
            content_padding=ft.padding.symmetric(vertical=14, horizontal=12),
            on_submit=self._login_clicked_handler, # Ensure handler is method
        )
        self.password_field = ft.TextField(
            label="Password",
            password=True,
            can_reveal_password=True,
            expand=True,
            border_radius=8,
            prefix_icon=ft.Icons.LOCK_OUTLINE_ROUNDED,
            on_submit=self._login_clicked_handler, # Ensure handler is method
            content_padding=ft.padding.symmetric(vertical=14, horizontal=12)
        )
        self.error_text = ft.Text(
            visible=False,
            weight=ft.FontWeight.W_500,
            color=ft.Colors.RED_700,
            text_align=ft.TextAlign.CENTER # Center error text
        )
        self.login_button = ft.FilledButton(
            text="Login",
            expand=True, # Button expands
            height=48,
            on_click=self._login_clicked_handler, # Ensure handler is method
            icon=ft.Icons.LOGIN_ROUNDED,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)) # Consistent radius
        )
        self.content = self._build_layout()

    def _build_layout(self) -> ft.Column:
        return ft.Column(
            controls=[
                ft.Text(
                    "Welcome Back!",
                    style=ft.TextThemeStyle.HEADLINE_SMALL,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(
                    "Sign in to access your account.",
                    style=ft.TextThemeStyle.BODY_LARGE,
                    color=ft.Colors.ON_SURFACE_VARIANT,
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
            spacing=12,
        )

    def _login_clicked_handler(self, e: Optional[ft.ControlEvent] = None): # Made method, accept event
        self.error_text.value = ""
        self.error_text.visible = False
        self.update() # Update to hide previous error immediately

        username = self.username_field.value.strip() if self.username_field.value else ""
        password = self.password_field.value if self.password_field.value else ""

        try:
            with get_db_session() as db:
                # Detach user_obj from session before passing to on_login_success if it causes issues
                user_obj = self.auth_service.authenticate_user(db, username, password)
                # db.expunge(user_obj) # Optional: if DetachedInstanceError is persistent
            self.on_login_success(user_obj)
        except (AuthenticationError, ValidationError) as ex:
            self.error_text.value = ex.message
            self.error_text.visible = True
        except DetachedInstanceError as di_err: # Specific SQLAlchemy error
            logger.error(f"SQLAlchemy DetachedInstanceError during/after login success: {di_err}", exc_info=True)
            self.error_text.value = "Login successful, but a session error occurred. Please retry."
            # Consider a more user-friendly message or specific recovery if possible.
            self.error_text.visible = True
        except Exception as ex_general: # Catch any other unexpected errors
            logger.error(f"Unexpected error in login: {ex_general}", exc_info=True)
            self.error_text.value = "An unexpected error occurred. Please try again."
            self.error_text.visible = True

        if self.page: self.page.update() # Update the page to reflect changes in the form