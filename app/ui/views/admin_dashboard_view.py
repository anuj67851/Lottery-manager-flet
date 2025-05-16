"""
Admin dashboard view for the application.

This module provides a Flet view for the admin dashboard.
"""
import flet as ft

class AdminDashboardView(ft.Container):
    """
    A view component for the admin dashboard.
    """
    
    def __init__(self, page: ft.Page, router, **params):
        """
        Initialize the admin dashboard view.
        
        Args:
            page (ft.Page): The Flet page.
            router: The router for navigation.
            **params: Additional parameters.
        """
        super().__init__()
        self.page = page
        self.router = router
        
        # Set page properties
        self.page.title = "Admin Dashboard - Lottery Manager"
    
    def build(self):
        """
        Build the admin dashboard view.
        
        Returns:
            ft.Control: The built view.
        """
        return ft.Column(
            controls=[
                ft.AppBar(
                    title=ft.Text("Admin Dashboard"),
                    bgcolor=ft.colors.BLUE,
                    color=ft.colors.WHITE,
                    actions=[
                        ft.IconButton(
                            icon=ft.icons.LOGOUT,
                            tooltip="Logout",
                            on_click=self.logout,
                        ),
                    ],
                ),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("Welcome to the Admin Dashboard", size=30, weight=ft.FontWeight.BOLD),
                            ft.Text("This is a placeholder for the admin dashboard view.", size=16),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    padding=50,
                    alignment=ft.alignment.center,
                ),
            ],
        )
    
    def logout(self, e):
        """
        Handle logout button click event.
        
        Args:
            e: The click event.
        """
        self.router.navigate_to("login")