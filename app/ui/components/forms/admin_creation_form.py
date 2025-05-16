import flet as ft
from typing import Callable

from app.data.crud_users import create_user
from app.data.database import get_db_session
from app.constants import ADMIN_ROLE
from app.core.exceptions import DatabaseError, ValidationError

class AdminCreationForm(ft.Container):
    def __init__(self, page: ft.Page, on_admin_created: Callable[[], None]):
        super().__init__()
        self.page = page
        self.on_admin_created = on_admin_created

        self.username_field = ft.TextField(
            label="Admin Username",
            autofocus=True,
            expand=True,
            border_radius=8,
            prefix_icon=ft.Icons.PERSON_ADD_ALT_1_ROUNDED,
            content_padding=ft.padding.symmetric(vertical=14, horizontal=12)
        )
        self.password_field = ft.TextField(
            label="Choose Password",
            password=True,
            can_reveal_password=True,
            expand=True,
            border_radius=8,
            prefix_icon=ft.Icons.LOCK_PERSON_ROUNDED,
            content_padding=ft.padding.symmetric(vertical=14, horizontal=12)
        )
        self.confirm_password_field = ft.TextField(
            label="Confirm Password",
            password=True,
            can_reveal_password=True,
            expand=True,
            border_radius=8,
            prefix_icon=ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED,
            on_submit=self.create_clicked,
            content_padding=ft.padding.symmetric(vertical=14, horizontal=12)
        )
        self.error_text = ft.Text(
            visible=False,
            weight=ft.FontWeight.W_500
        )
        self.create_button = ft.FilledButton(
            text="Create Admin Account",
            expand=True,
            height=48,
            on_click=self.create_clicked,
            icon=ft.Icons.PERSON_ADD_ROUNDED
        )
        self.content = self._build_layout()

    def _build_layout(self):
        return ft.Column(
            controls=[
                ft.Text(
                    "Setup Administrator",
                    style=ft.TextThemeStyle.HEADLINE_SMALL,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(
                    "Create the first admin user for the system.",
                    style=ft.TextThemeStyle.BODY_LARGE,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=20),
                self.username_field,
                self.password_field,
                self.confirm_password_field,
                self.error_text,
                ft.Container(height=15),
                self.create_button,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            spacing=12,
        )

    def create_clicked(self, e=None):
        self.error_text.value = ""
        self.error_text.visible = False
        self.error_text.update()

        username = self.username_field.value
        password = self.password_field.value
        confirm_password = self.confirm_password_field.value

        error_message = None
        if not username:
            error_message = "Admin Username is required"
        elif not password:
            error_message = "Password is required"
        elif password != confirm_password:
            error_message = "Passwords do not match"

        if error_message:
            self.error_text.value = error_message
            self.error_text.visible = True
            self.error_text.update()
            return

        try:
            with get_db_session() as db:
                create_user(db, username, password, role=ADMIN_ROLE)
            self.on_admin_created()
        except (DatabaseError, ValidationError) as ex:
            self.error_text.value = ex.message
            self.error_text.visible = True
            self.error_text.update()
        except Exception as ex_general:
            print(f"Unexpected error in admin creation: {ex_general}")
            self.error_text.value = "An unexpected error occurred. Please try again."
            self.error_text.visible = True
            self.error_text.update()