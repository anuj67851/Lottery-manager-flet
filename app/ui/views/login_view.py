import flet as ft

from app.core.auth_service import AuthService
from app.ui.components.login_form import LoginForm
from app.ui.components.admin_creation_form import AdminCreationForm
from app.data.crud_users import any_users_exist
from app.data.database import get_db_session
from app.constants import ADMIN_ROLE, ADMIN_DASHBOARD_ROUTE, EMPLOYEE_DASHBOARD_ROUTE, LOGIN_ROUTE
from app.core.models import User

class LoginView(ft.Container):
    def __init__(self, page: ft.Page, router, **params):
        super().__init__(expand=True, alignment=ft.alignment.center)
        self.page = page
        self.router = router

        self.page.appbar = self._build_appbar()

        with get_db_session() as db:
            users_exist = any_users_exist(db)
            if users_exist:
                self.current_form = LoginForm(page=self.page, on_login_success=self.on_login_success)
            else:
                self.current_form = AdminCreationForm(page=self.page, on_admin_created=self.on_admin_created)

        self.content = self._build_layout() # This is the body of the login page

    def _build_appbar(self):
        return ft.AppBar(
            title=ft.Text("Lottery Management System"),
            bgcolor=ft.Colors.BLUE_700,
            color=ft.Colors.WHITE,
        )

    def _build_layout(self):
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
                    content=self.current_form,
                    padding=30,
                    border_radius=12,
                    bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.BLACK),
                    shadow=ft.BoxShadow(
                        spread_radius=1,
                        blur_radius=10,
                        color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK26),
                        offset=ft.Offset(0, 4),
                    ),
                    width=400,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            expand=True,
        )

    def on_login_success(self, user: User):
        user_params = {"current_user": user}

        if AuthService.get_user_role(user) == ADMIN_ROLE:
            self.router.navigate_to(ADMIN_DASHBOARD_ROUTE, **user_params)
        else:
            self.router.navigate_to(EMPLOYEE_DASHBOARD_ROUTE, **user_params)

    def on_admin_created(self):
        self.page.open(
            ft.SnackBar(
                content=ft.Text("Admin user created successfully! Please log in."),
                open=True
            )
        )
        self.router.navigate_to(LOGIN_ROUTE)