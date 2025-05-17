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
from app.ui.components.forms.sales_person_creation_form import SalesPersonCreationForm


class LoginView(ft.Container):
    def __init__(self, page: ft.Page, router, **params):
        super().__init__(expand=True, alignment=ft.alignment.center)
        self.page = page
        self.router = router
        self.user_service = UserService()
        self.license_service = LicenseService()
        self.auth_service = AuthService()

        self.page.appbar = self._build_appbar()
        self.current_form_container = ft.Container(width=400) # Placeholder for form
        self.content = self._build_layout() # Build base layout first
        self._check_initial_setup()         # Then determine which form to show

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
                    bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.BLACK), # Kept original style
                    shadow=ft.BoxShadow(
                        spread_radius=1,
                        blur_radius=10,
                        color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK26), # Kept original style
                        offset=ft.Offset(0, 4),
                    ),
                    # width=400, # Width applied to current_form_container directly
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            expand=True,
        )

    def _check_initial_setup(self):
        with get_db_session() as db:
            users_exist = self.user_service.any_users_exist(db)

        if not users_exist:
            # No users exist, show Admin Creation Form
            admin_form = SalesPersonCreationForm(page=self.page, on_admin_created=self._on_sales_person_created_successfully)
            self.current_form_container.content = admin_form
        else:
            # Users exist, show Login Form
            login_form = LoginForm(page=self.page, on_login_success=self.on_login_success)
            self.current_form_container.content = login_form

        if self.page: self.page.update()


    def _on_sales_person_created_successfully(self):
        # After sales person is created, switch to login form
        login_form = LoginForm(page=self.page, on_login_success=self.on_login_success)
        self.current_form_container.content = login_form
        if self.page: self.page.update()


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
                    content=ft.Text("License not activated. Please contact your salesperson or activate the license."),
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