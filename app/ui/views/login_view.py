import flet as ft

from app.services.auth_service import AuthService
from app.services.configuration_service import ConfigurationService
from app.services.user_service import UserService
from app.ui.components.forms.login_form import LoginForm
from app.data.database import get_db_session
from app.constants import (
    ADMIN_ROLE, ADMIN_DASHBOARD_ROUTE,
    EMPLOYEE_DASHBOARD_ROUTE, EMPLOYEE_ROLE,
    SALESPERSON_DASHBOARD_ROUTE, SALESPERSON_ROLE,
)
from app.core.models import User
from app.ui.components.common.appbar_factory import create_appbar # Import AppBar factory
from app.config import APP_TITLE # Use APP_TITLE from config

class LoginView(ft.Container):
    def __init__(self, page: ft.Page, router, **params):
        super().__init__(expand=True, alignment=ft.alignment.center)
        self.page = page
        self.router = router
        # Services are typically not instantiated per view, but rather passed or accessed globally/via DI.
        # For simplicity here, keeping them as instance variables if needed by methods in this view.
        self.user_service = UserService()
        self.license_service = ConfigurationService()
        self.auth_service = AuthService() # AuthService will be used by LoginForm

        self.page.appbar = create_appbar(
            page=self.page,
            router=self.router, # Pass router for logout
            title_text=APP_TITLE, # Use app title from config
            show_logout_button=False, # No logout button on login screen
            show_user_info=False,     # No user info on login screen
            show_license_status=False # No license status on login screen
        )

        self.login_form_component = LoginForm(page=self.page, on_login_success=self._handle_login_success)
        # current_form_container is now self.login_form_component
        self.content = self._build_layout()

    def _build_layout(self) -> ft.Column:
        return ft.Column(
            [
                ft.Container(
                    content=ft.Icon(
                        ft.Icons.LOCK_PERSON_OUTLINED,
                        color=ft.Colors.BLUE_GREY_300, # Use a theme-aware color if possible
                        size=80,
                    ),
                    padding=ft.padding.only(bottom=20),
                ),
                ft.Container(
                    content=self.login_form_component, # The LoginForm instance
                    padding=30,
                    border_radius=ft.border_radius.all(12),
                    bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLACK), # Subtle background for the form card
                    # Use theme surface color if available, e.g., self.page.theme.surfaceVariant
                    shadow=ft.BoxShadow(
                        spread_radius=1, blur_radius=15,
                        color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK26),
                        offset=ft.Offset(0, 5),
                    ),
                    width=400, # Fixed width for the login card
                ),
                ft.Container(
                    content=ft.Text(
                        "© 2025 Anuj Patel · All Rights Reserved · Built using Python and Flet",
                        size=12,
                        color=ft.Colors.GREY_500, # Softer color
                        text_align=ft.TextAlign.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    padding=10,
                    margin=ft.margin.only(top=30), # More space from form
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20, # Spacing between elements in the Column
            expand=True,
        )

    def _handle_login_success(self, user: User): # Renamed from on_login_success
        # This method is called by LoginForm upon successful authentication
        user_params = {"current_user": user} # Params for the next view
        user_role = self.auth_service.get_user_role(user) # AuthService already used by LoginForm

        license_activated = False # Default
        try:
            with get_db_session() as db:
                license_activated = self.license_service.get_license_status(db)
        except Exception as e:
            print(f"Error fetching license status: {e}")
            # Show error to user, prevent login, or proceed with license_activated = False
            self.page.open(ft.SnackBar(ft.Text("Could not verify license status. Please try again."), open=True, bgcolor=ft.Colors.ERROR))
            return # Stay on login page

        user_params["license_status"] = license_activated

        # Route based on role and license status
        if user_role == SALESPERSON_ROLE:
            self.router.navigate_to(SALESPERSON_DASHBOARD_ROUTE, **user_params)
        elif license_activated: # Admin or Employee require active license
            if user_role == ADMIN_ROLE:
                self.router.navigate_to(ADMIN_DASHBOARD_ROUTE, **user_params)
            elif user_role == EMPLOYEE_ROLE:
                self.router.navigate_to(EMPLOYEE_DASHBOARD_ROUTE, **user_params)
            else: # Should not happen with defined roles
                self.page.open(ft.SnackBar(ft.Text(f"Unknown user role '{user_role}'. Access denied."), open=True, bgcolor=ft.Colors.ERROR))
                # Potentially log this unexpected state
                # self.router.navigate_to(LOGIN_ROUTE) # Fallback to login
        else: # Admin/Employee tried to log in with inactive license
            self.page.open(
                ft.SnackBar(
                    content=ft.Text("License not active. Please contact your salesperson to activate."),
                    open=True, duration=5000 # Longer duration for important message
                )
            )
            # User stays on login page. LoginForm will clear fields or user can retry.