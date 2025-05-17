import flet as ft
from typing import Callable

from app.services.user_service import UserService # Use UserService
from app.data.database import get_db_session
from app.constants import SALESPERSON_ROLE
from app.core.exceptions import DatabaseError, ValidationError

class SalesPersonCreationForm(ft.Container):
    def __init__(self, page: ft.Page, on_sales_person_created: Callable[[], None]):
        super().__init__()
        self.page = page
        self.on_sales_person_created = on_sales_person_created
        self.user_service = UserService() # Instantiate UserService

        self.username_field = ft.TextField(
            label="Sales Person Username",
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
            weight=ft.FontWeight.W_500,
            color=ft.Colors.RED_700
        )
        self.create_button = ft.FilledButton(
            text="Create Sales Person Account",
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
                    "Setup Sales Person",
                    style=ft.TextThemeStyle.HEADLINE_SMALL,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(
                    "Create the first user for the system.",
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

        username = self.username_field.value.strip()
        password = self.password_field.value
        confirm_password = self.confirm_password_field.value

        error_message = None
        if not username:
            error_message = "Username is required"
        elif not password:
            error_message = "Password is required"
        elif len(password) < 6: # Example: Basic password policy
            error_message = "Password must be at least 6 characters long"
        elif password != confirm_password:
            error_message = "Passwords do not match"

        if error_message:
            self.error_text.value = error_message
            self.error_text.visible = True
            if self.page: self.page.update() # Ensure page updates error text visibility
            return

        try:
            with get_db_session() as db:
                self.user_service.create_user(db, username, password, role=SALESPERSON_ROLE)
            # Show success SnackBar
            if self.page:
                self.page.open(ft.SnackBar(ft.Text(f"Sales User '{username}' created successfully!"), open=True))
            self.on_sales_person_created() # Callback to, e.g., navigate to login
        except (DatabaseError, ValidationError) as ex:
            self.error_text.value = ex.message
            self.error_text.visible = True
        except Exception as ex_general:
            print(f"Unexpected error in user creation: {ex_general}")
            self.error_text.value = "An unexpected error occurred. Please try again."
            self.error_text.visible = True

        if self.page: self.page.update()