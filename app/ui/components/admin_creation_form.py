import flet as ft
from typing import Callable

from app.data.crud_users import create_user
from app.data.database import get_db_session
from app.constants import ADMIN_ROLE
from app.core.exceptions import DatabaseError, ValidationError

class AdminCreationForm(ft.Container):
    def __init__(self, page: ft.Page, on_admin_created: Callable[[], None]): # Added page parameter
        super().__init__(padding=10, border_radius=10)
        self.page = page # Store the page reference
        self.on_admin_created = on_admin_created

        self.username_field = ft.TextField(
            label="Admin Username",
            autofocus=True,
            width=300,
        )
        self.password_field = ft.TextField(
            label="Password",
            password=True,
            can_reveal_password=True,
            width=300,
        )
        self.confirm_password_field = ft.TextField(
            label="Confirm Password",
            password=True,
            can_reveal_password=True,
            width=300,
        )
        self.error_text = ft.Text(
            color=ft.Colors.RED,
            visible=False,
        )
        self.create_button = ft.ElevatedButton(
            text="Create Admin User",
            width=300,
            on_click=self.create_clicked,
        )
        self.content = self._build_layout()

    def _build_layout(self):
        return ft.Column(
            controls=[
                ft.Text("Create Admin User", size=30, weight=ft.FontWeight.BOLD),
                ft.Text("No users exist. Please create an admin user to get started.", size=16),
                ft.Container(height=20),
                self.username_field,
                self.password_field,
                self.confirm_password_field,
                self.error_text,
                ft.Container(height=10),
                self.create_button,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        )

    def create_clicked(self, e):
        # 1. Clear previous error and update only the error text control
        self.error_text.value = ""
        self.error_text.visible = False
        self.error_text.update() # Update specific control

        # 2. Get form values
        username = self.username_field.value
        password = self.password_field.value
        confirm_password = self.confirm_password_field.value

        # 3. Client-side validation
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
            self.error_text.update() # Update specific control
            return

        # 4. Perform backend operation
        try:
            with get_db_session() as db:
                create_user(db, username, password, role=ADMIN_ROLE)
            # If successful, the on_admin_created callback will handle navigation
            # and the router will update the page.
            self.on_admin_created()
        except (DatabaseError, ValidationError) as ex:
            self.error_text.value = ex.message
            self.error_text.visible = True
            self.error_text.update() # Update specific control
        except Exception as ex_general: # Catch any other unexpected errors
            print(f"Unexpected error in admin creation: {ex_general}") # For debugging
            self.error_text.value = "An unexpected error occurred. Please try again."
            self.error_text.visible = True
            self.error_text.update() # Update specific control