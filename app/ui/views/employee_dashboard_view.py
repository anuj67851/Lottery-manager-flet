import flet as ft
from app.core.models import User
from app.ui.components.common.appbar_factory import create_appbar # Import AppBar factory
from app.constants import SALES_ENTRY_ROUTE, EMPLOYEE_DASHBOARD_ROUTE # Import constants
from app.ui.components.widgets.function_button import create_nav_card_button # Import button factory

class EmployeeDashboardView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user: User, license_status: bool, **params):
        super().__init__(expand=True)
        self.page = page
        self.router = router
        self.current_user = current_user
        self.license_status = license_status

        # Navigation parameters for views launched from this dashboard
        self.navigation_params_for_children = {
            "current_user": self.current_user,
            "license_status": self.license_status,
            "previous_view_route": EMPLOYEE_DASHBOARD_ROUTE, # This view is the previous one
            "previous_view_params": { # Params to return to this view (EmployeeDashboardView itself)
                "current_user": self.current_user,
                "license_status": self.license_status,
            },
        }

        self.page.appbar = create_appbar(
            page=self.page,
            router=self.router,
            title_text="Employee Dashboard",
            current_user=self.current_user,
            license_status=self.license_status, # Show license status for employee
            show_user_info=True
        )
        self.content = self._build_body()

    def _build_body(self) -> ft.Container:
        welcome_message = "Welcome, Employee!"
        if self.current_user and self.current_user.username:
            welcome_message = f"Welcome, {self.current_user.username}!"

        sales_entry_button = create_nav_card_button(
            router=self.router,
            text="Sales Entry",
            icon_name=ft.Icons.POINT_OF_SALE_ROUNDED,
            accent_color=ft.Colors.GREEN_700,
            navigate_to_route=SALES_ENTRY_ROUTE,
            tooltip="Access the sales entry screen to record daily sales",
            router_params=self.navigation_params_for_children, # Pass necessary params
            height=180, # Make it a bit larger and more prominent
            width=200,
            icon_size=50,
            disabled=not self.license_status # Disable if license is not active
        )

        if not self.license_status:
            sales_entry_button.tooltip = "Sales Entry (License Inactive)"


        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(welcome_message, size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                    ft.Container(height=20), # Spacer
                    ft.Text(
                        "Use the button below to record daily sales.",
                        size=16,
                        text_align=ft.TextAlign.CENTER,
                        color=ft.Colors.ON_SURFACE_VARIANT
                    ),
                    ft.Container(height=30), # Spacer
                    ft.Row(
                        [sales_entry_button],
                        alignment=ft.MainAxisAlignment.CENTER # Center the button
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=20,
            ),
            padding=50,
            alignment=ft.alignment.center,
            expand=True
        )