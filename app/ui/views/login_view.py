import flet as ft

from app.services.auth_service import AuthService
from app.services.configuration_service import ConfigurationService
from app.services.user_service import UserService
from app.ui.components.forms.login_form import LoginForm
from app.constants import (
    ADMIN_ROLE, ADMIN_DASHBOARD_ROUTE,
    EMPLOYEE_DASHBOARD_ROUTE, EMPLOYEE_ROLE,
    SALESPERSON_DASHBOARD_ROUTE, SALESPERSON_ROLE,
)
from app.core.models import User
from app.ui.components.common.appbar_factory import create_appbar
from app.config import APP_TITLE, VERSION

class LoginView(ft.Container):
    def __init__(self, page: ft.Page, router, **params):
        super().__init__(expand=True, alignment=ft.alignment.center)
        self.page = page
        self.router = router
        self.user_service = UserService()
        self.config_service = ConfigurationService() # Instantiated
        self.auth_service = AuthService()

        self.page.appbar = create_appbar(
            page=self.page,
            router=self.router,
            title_text=APP_TITLE,
            show_logout_button=False,
            show_user_info=False,
            show_license_status=False
        )

        self.login_form_component = LoginForm(page=self.page, on_login_success=self._handle_login_success)
        self.content = self._build_layout()

    def _build_layout(self) -> ft.Column:
        return ft.Column(
            [
                ft.Container(
                    content=ft.Icon(
                        ft.Icons.LOCK_PERSON_OUTLINED,
                        color=ft.Colors.BLUE_GREY_300,
                        size=80,
                    ),
                    padding=ft.padding.only(bottom=20),
                ),
                ft.Container(
                    content=self.login_form_component,
                    padding=30,
                    border_radius=ft.border_radius.all(12),
                    bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLACK),
                    shadow=ft.BoxShadow(
                        spread_radius=1, blur_radius=15,
                        color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK26),
                        offset=ft.Offset(0, 5),
                    ),
                    width=400,
                ),
                ft.Container(
                    content=ft.Text(
                        f"© 2025 Anuj Patel · All Rights Reserved · Built using Python and Flet · Version: {VERSION}",
                        size=12,
                        color=ft.Colors.GREY_500,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    padding=10,
                    margin=ft.margin.only(top=30),
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            expand=True,
        )

    def _handle_login_success(self, user: User):
        user_params = {"current_user": user}
        user_role = self.auth_service.get_user_role(user)

        license_activated = False
        try:
            # License status is now read from the file via ConfigurationService
            license_activated = self.config_service.get_license_status()
        except Exception as e:
            print(f"Error fetching license status from file: {e}")
            self.page.open(ft.SnackBar(ft.Text("Could not verify license status. Please try again."), open=True, bgcolor=ft.Colors.ERROR))
            return

        user_params["license_status"] = license_activated

        if user_role == SALESPERSON_ROLE:
            # Salesperson can always log in, their dashboard handles license activation.
            self.router.navigate_to(SALESPERSON_DASHBOARD_ROUTE, **user_params)
        elif license_activated: # Admin or Employee require active license to proceed
            if user_role == ADMIN_ROLE:
                self.router.navigate_to(ADMIN_DASHBOARD_ROUTE, **user_params)
            elif user_role == EMPLOYEE_ROLE:
                self.router.navigate_to(EMPLOYEE_DASHBOARD_ROUTE, **user_params)
            else: # Should not happen with defined roles
                self.page.open(ft.SnackBar(ft.Text(f"Unknown user role '{user_role}'. Access denied."), open=True, bgcolor=ft.Colors.ERROR))
        else: # Admin/Employee tried to log in with inactive license
            self.page.open(
                ft.SnackBar(
                    content=ft.Text("License not active. Please contact your salesperson/owner to activate."),
                    open=True, duration=5000
                )
            )