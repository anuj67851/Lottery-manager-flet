"""
Employee dashboard view for the application.

This module provides a Flet view for the employee dashboard.
"""
import flet as ft

class EmployeeDashboardView(ft.Container):
    """
    A view component for the employee dashboard.
    """
    
    def __init__(self, page: ft.Page, router, **params):
        """
        Initialize the employee dashboard view.
        
        Args:
            page (ft.Page): The Flet page.
            router: The router for navigation.
            **params: Additional parameters.
        """
        super().__init__()
        self.page = page
        self.router = router
        
        # Set page properties
        self.page.title = "Employee Dashboard - Lottery Manager"
    
    def build(self):
        """
        Build the employee dashboard view.
        
        Returns:
            ft.Control: The built view.
        """
        return ft.Column(
            controls=[
                ft.AppBar(
                    title=ft.Text("Employee Dashboard"),
                    bgcolor=ft.colors.GREEN,
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
                            ft.Text("Welcome to the Employee Dashboard", size=30, weight=ft.FontWeight.BOLD),
                            ft.Text("This is a placeholder for the employee dashboard view.", size=16),
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