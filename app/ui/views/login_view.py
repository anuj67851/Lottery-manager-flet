import flet as ft

from app.services.auth_service import AuthService
from app.services.license_service import LicenseService
from app.services.user_service import UserService
from app.ui.components.forms.login_form import LoginForm
from app.data.database import get_db_session
from app.constants import (
    ADMIN_ROLE, ADMIN_DASHBOARD_ROUTE,
    EMPLOYEE_DASHBOARD_ROUTE, EMPLOYEE_ROLE,
    SALESPERSON_DASHBOARD_ROUTE, SALESPERSON_ROLE,
    LOGIN_ROUTE
)
from app.core.models import User


class LoginView(ft.Container):
    def __init__(self, page: ft.Page, router, **params):
        super().__init__(expand=True, alignment=ft.alignment.center)
        self.page = page
        self.router = router
        self.user_service = UserService()
        self.license_service = LicenseService()
        self.auth_service = AuthService()
        self.page.appbar = self._build_appbar()
        
        login_form = LoginForm(page=self.page, on_login_success=self.on_login_success)
        self.current_form_container = login_form # Placeholder for form
        self.content = self._build_layout() # Build base layout first

    def _build_appbar(self):
        return ft.AppBar(
            title=ft.Text("Lottery Management System"),
            bgcolor=ft.Colors.BLUE_700, # Kept original color
            color=ft.Colors.WHITE,      # Kept original color
        )

    def _build_layout(self):
        # The self.current_form_container will hold either Login or AdminCreationForm
        return ft.Column(
            [
                ft.Container(
                    content=ft.Icon(
                        ft.Icons.LOCK_PERSON_OUTLINED, # Kept original icon
                        color=ft.Colors.BLUE_GREY_300, # Kept original color
                        size=80,
                    ),
                    padding=ft.padding.only(bottom=20),
                ),
                ft.Container(
                    content=self.current_form_container, # This is where the form goes
                    padding=30,
                    border_radius=12,
                    bgcolor=ft.Colors.WHITE70, # Kept original style
                    shadow=ft.BoxShadow(
                        spread_radius=1,
                        blur_radius=10,
                        color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK26), # Kept original style
                        offset=ft.Offset(0, 4),
                    ),
                    width=400,
                ),
                ft.Container(
                    content=ft.Text(
                        "© 2025 Anuj Patel · All Rights Reserved · Built using Python and Flet",
                        size=12,
                        color=ft.Colors.GREY_400,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    padding=10,
                    margin=ft.margin.only(top=10),
                ),

            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            expand=True,
        )

    def on_login_success(self, user: User):
        user_params = {"current_user": user}
        user_role = self.auth_service.get_user_role(user)

        license_activated = False
        with get_db_session() as db:
            license_activated = self.license_service.get_license_status(db)

        user_params["license_status"] = license_activated

        if user_role == SALESPERSON_ROLE:
            self.router.navigate_to(SALESPERSON_DASHBOARD_ROUTE, **user_params)
        elif license_activated:
            if user_role == ADMIN_ROLE:
                self.router.navigate_to(ADMIN_DASHBOARD_ROUTE, **user_params)
            elif user_role == EMPLOYEE_ROLE:
                self.router.navigate_to(EMPLOYEE_DASHBOARD_ROUTE, **user_params)
            else: # Should not happen if roles are well-defined
                self.page.open(ft.SnackBar(ft.Text("Unknown user role after login."), open=True, bgcolor=ft.Colors.ERROR))
                self.router.navigate_to(LOGIN_ROUTE) # Fallback to login
        else: # License not activated for Admin/Employee
            self.page.open(
                ft.SnackBar(
                    content=ft.Text("License not activated. Please contact your salesperson to activate the license."),
                    open=True,
                    duration=4000
                )
            )
            # Do not navigate away, user stays on login page or current form
            # If they are salesperson, they would have already navigated.
            # This means an admin/employee tried to log in with inactive license.
            # self.router.navigate_to(LOGIN_ROUTE) # Or stay on login page
            # Let them retry or wait for salesperson to activate license.
            # If the current form is AdminCreationForm, it's fine. If LoginForm, they can retry.