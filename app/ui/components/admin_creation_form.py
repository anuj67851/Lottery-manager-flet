"""
Admin creation form component for the application.

This module provides a Flet component for creating the first admin user.
"""
import flet as ft
from typing import Callable

from app.data.crud_users import create_user
from app.data.database import get_db_session

class AdminCreationForm(ft.Container):
    """
    A form component for creating the first admin user.
    """
    
    def __init__(self, on_admin_created: Callable[[], None]):
        """
        Initialize the admin creation form.
        
        Args:
            on_admin_created (Callable[[], None]): Callback function to be called when admin is created.
        """
        super().__init__()
        self.on_admin_created = on_admin_created
        
        # Create form fields
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
    
    def build(self):
        """
        Build the admin creation form component.
        
        Returns:
            ft.Control: The built component.
        """
        return ft.Column(
            controls=[
                ft.Text("Create Admin User", size=30, weight=ft.FontWeight.BOLD),
                ft.Text("No users exist in the system. Please create an admin user to get started.", size=16),
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
        """
        Handle create button click event.
        
        Args:
            e: The click event.
        """
        # Clear previous error
        self.error_text.visible = False
        self.update()
        
        # Get form values
        username = self.username_field.value
        password = self.password_field.value
        confirm_password = self.confirm_password_field.value
        
        # Validate form
        if not username:
            self.error_text.value = "Username is required"
            self.error_text.visible = True
            self.update()
            return
        
        if not password:
            self.error_text.value = "Password is required"
            self.error_text.visible = True
            self.update()
            return
        
        if password != confirm_password:
            self.error_text.value = "Passwords do not match"
            self.error_text.visible = True
            self.update()
            return
        
        # Create admin user
        with get_db_session() as db:
            try:
                create_user(db, username, password, role="admin")
                # Call success callback
                self.on_admin_created()
            except Exception as e:
                self.error_text.value = f"Error creating admin user: {str(e)}"
                self.error_text.visible = True
                self.update()