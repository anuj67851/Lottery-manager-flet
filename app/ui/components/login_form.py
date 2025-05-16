"""
Login form component for the application.

This module provides a Flet component for user login.
"""
import flet as ft
from typing import Callable, Optional

from app.core.auth_service import AuthService
from app.data.database import get_db_session

class LoginForm(ft.Container):
    """
    A form component for user login.
    """
    
    def __init__(self, on_login_success: Callable[[str], None]):
        """
        Initialize the login form.
        
        Args:
            on_login_success (Callable[[str], None]): Callback function to be called when login is successful.
                The function will receive the user's role as a parameter.
        """
        super().__init__()
        self.on_login_success = on_login_success
        
        # Create form fields
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
            color=ft.colors.RED,
            visible=False,
        )
        
        self.login_button = ft.ElevatedButton(
            text="Login",
            width=300,
            on_click=self.login_clicked,
        )
    
    def build(self):
        """
        Build the login form component.
        
        Returns:
            ft.Control: The built component.
        """
        return ft.Column(
            controls=[
                ft.Text("Login", size=30, weight=ft.FontWeight.BOLD),
                ft.Text("Please enter your credentials to login", size=16),
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
        """
        Handle login button click event.
        
        Args:
            e: The click event.
        """
        # Clear previous error
        self.error_text.visible = False
        self.update()
        
        # Get username and password
        username = self.username_field.value
        password = self.password_field.value
        
        # Authenticate user
        with get_db_session() as db:
            try:
                success, user, error_message = AuthService.authenticate_user(db, username, password)

                if success and user:
                    # Get user role
                    role = AuthService.get_user_role(user)

                    # Call success callback with user role
                    self.on_login_success(role)
                else:
                    # Show error message
                    self.error_text.value = error_message
                    self.error_text.visible = True
                    self.update()
            except Exception as e:
                self.error_text.value = f"Error logging in: {str(e)}"
                self.error_text.visible = True
                self.update()