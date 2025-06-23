import flet as ft
from app.services import UserService
from app.data.database import get_db_session
from app.constants import SALESPERSON_ROLE, LOGIN_ROUTE
from app.core.exceptions import ValidationError, DatabaseError
from app.config import APP_TITLE
from app.ui.components.common.appbar_factory import create_appbar

import logging
logger = logging.getLogger("lottery_manager_app")

class FirstRunSetupView(ft.Container):
    def __init__(self, page: ft.Page, router, **params):
        super().__init__(expand=True, alignment=ft.alignment.center)
        self.page = page
        self.router = router
        self.user_service = UserService() # UserService now has enhanced validation

        self.page.appbar = create_appbar(
            page=self.page,
            router=self.router,
            title_text=f"{APP_TITLE} - Initial Setup",
            show_logout_button=False,
            show_user_info=False,
            show_license_status=False
        )

        self.admin_username_field = ft.TextField(
            label="Salesperson/Owner Username",
            autofocus=True,
            border_radius=8,
            prefix_icon=ft.Icons.PERSON_OUTLINE_ROUNDED,
            on_submit=self._create_initial_user_handler,
        )
        self.admin_password_field = ft.TextField(
            label="Password",
            password=True,
            can_reveal_password=True,
            border_radius=8,
            prefix_icon=ft.Icons.LOCK_OUTLINE_ROUNDED,
            on_submit=self._create_initial_user_handler,
        )
        self.admin_confirm_password_field = ft.TextField(
            label="Confirm Password",
            password=True,
            can_reveal_password=True,
            border_radius=8,
            prefix_icon=ft.Icons.LOCK_RESET_ROUNDED,
            on_submit=self._create_initial_user_handler,
        )
        self.error_text = ft.Text(
            visible=False,
            weight=ft.FontWeight.W_500,
            color=ft.Colors.RED_700,
            text_align=ft.TextAlign.CENTER
        )
        self.submit_button = ft.FilledButton(
            text="Create Salesperson Account",
            height=48,
            on_click=self._create_initial_user_handler,
            icon=ft.Icons.SUPERVISED_USER_CIRCLE_ROUNDED,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
        )
        self.content = self._build_layout()

    def _build_layout(self) -> ft.Column:
        return ft.Column(
            [
                ft.Text(
                    "Welcome! Let's set up your primary Salesperson/Owner account.",
                    style=ft.TextThemeStyle.HEADLINE_SMALL,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(
                    "This account will manage licenses and other system users.",
                    style=ft.TextThemeStyle.BODY_LARGE,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=20),
                self.admin_username_field,
                self.admin_password_field,
                self.admin_confirm_password_field,
                self.error_text,
                ft.Container(height=15),
                self.submit_button,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            spacing=12,
            width=400,
            alignment=ft.MainAxisAlignment.CENTER,
        )

    def _create_initial_user_handler(self, e: ft.ControlEvent):
        self.error_text.value = ""
        self.error_text.visible = False

        username = self.admin_username_field.value.strip() if self.admin_username_field.value else ""
        password = self.admin_password_field.value if self.admin_password_field.value else ""
        confirm_password = self.admin_confirm_password_field.value if self.admin_confirm_password_field.value else ""

        try:
            # UserService.create_user now handles all detailed validation
            if not confirm_password: # Explicit check for confirm_password as it's not directly validated in user_service
                raise ValidationError("Confirm Password field is required.")
            if password != confirm_password: # This check is still good here before calling service
                raise ValidationError("Passwords do not match.")

            with get_db_session() as db:
                self.user_service.create_user(db, username, password, SALESPERSON_ROLE)

            self.page.open(ft.SnackBar(
                ft.Text(f"Salesperson account '{username}' created successfully! Please log in."),
                open=True,
                duration=4000
            ))
            self.router.navigate_to(LOGIN_ROUTE)

        except (ValidationError, DatabaseError) as ex:
            self.error_text.value = ex.message
            self.error_text.visible = True
            if self.error_text.page: self.error_text.update()
        except Exception as ex_general:
            self.error_text.value = "An unexpected error occurred. Please try again."
            self.error_text.visible = True
            logger.error(f"Unexpected error during first run setup: {ex_general}", exc_info=True)
            if self.error_text.page: self.error_text.update()

        # No page.update() needed here if individual controls are updated.