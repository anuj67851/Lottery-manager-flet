import flet as ft

from app.constants import EMPLOYEE_ROLE, MANAGED_USER_ROLES, ADMIN_DASHBOARD_ROUTE
from app.core.models import User
from app.core.exceptions import ValidationError, DatabaseError
from app.services.user_service import UserService
from app.data.database import get_db_session
from app.ui.components.common.search_bar_component import SearchBarComponent
from app.ui.components.tables.users_table import UsersTable
from app.ui.components.common.appbar_factory import create_appbar
from app.ui.components.common.dialog_factory import create_form_dialog


class AdminUserManagementView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user: User, license_status: bool,
                 previous_view_route: str = ADMIN_DASHBOARD_ROUTE,
                 previous_view_params: dict = None,
                 **params):
        super().__init__(expand=True, padding=0)
        self.page = page
        self.router = router
        self.current_user = current_user # This is the Admin performing actions
        self.license_status = license_status
        self.previous_view_route = previous_view_route
        self.previous_view_params = previous_view_params if previous_view_params is not None else {}

        self.user_service = UserService()

        self.search_bar = SearchBarComponent(
            on_search_changed=self._on_search_term_changed,
            label="Search Users (Username, Role)",
            expand=True
        )

        self.page.appbar = create_appbar(
            page=self.page,
            router=self.router,
            title_text=f"{self.current_user.role.capitalize()} > User Management",
            current_user=self.current_user,
            license_status=self.license_status,
            leading_widget=ft.IconButton(
                icon=ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                tooltip="Go Back to Admin Dashboard",
                icon_color=ft.Colors.WHITE,
                on_click=self._go_back
            )
        )

        self.users_table_component = UsersTable(
            page=self.page,
            user_service=self.user_service,
            initial_roles_to_display=MANAGED_USER_ROLES, # Admin manages Admin and Employee roles
            current_acting_user=self.current_user, # Pass the admin user
            on_data_changed_callback=self._handle_table_data_change
        )

        self.content = self._build_body()
        self.users_table_component.refresh_data_and_ui()

    def _go_back(self, e):
        nav_params = {**self.previous_view_params}
        if "current_user" not in nav_params and self.current_user:
            nav_params["current_user"] = self.current_user
        if "license_status" not in nav_params and self.license_status is not None:
            nav_params["license_status"] = self.license_status
        self.router.navigate_to(self.previous_view_route, **nav_params)

    def _on_search_term_changed(self, search_term: str):
        self.users_table_component.refresh_data_and_ui(search_term=search_term)

    def _handle_add_user_click(self, e):
        self._open_add_user_dialog()

    def _close_active_dialog(self, e=None):
        if self.page.dialog:
            self.page.close(self.page.dialog)
            self.page.update()

    def _open_add_user_dialog(self):
        username_field = ft.TextField(label="Username", autofocus=True, border_radius=8)
        password_field = ft.TextField(label="Password", password=True, can_reveal_password=True, border_radius=8)
        confirm_password_field = ft.TextField(label="Confirm Password", password=True, can_reveal_password=True, border_radius=8)
        # Admin can create Admin or Employee roles
        role_options = [ft.dropdown.Option(role, role.capitalize()) for role in MANAGED_USER_ROLES]
        role_dropdown = ft.Dropdown(label="Role", options=role_options, value=EMPLOYEE_ROLE, border_radius=8) # Default to Employee
        error_text_add = ft.Text(visible=False, color=ft.Colors.RED_700)

        form_column = ft.Column(
            [username_field, password_field, confirm_password_field, role_dropdown, error_text_add],
            tight=True, spacing=15, scroll=ft.ScrollMode.AUTO,
        )

        def _save_new_user_handler(e):
            error_text_add.value = ""
            error_text_add.visible = False

            username = username_field.value.strip() if username_field.value else ""
            password = password_field.value if password_field.value else ""
            confirm_password = confirm_password_field.value if confirm_password_field.value else ""
            role = role_dropdown.value

            try:
                if not username or not password or not role or not confirm_password:
                    raise ValidationError("All fields (Username, Password, Role) are required.")
                if password != confirm_password:
                    raise ValidationError("Passwords do not match.")

                with get_db_session() as db:
                    self.user_service.create_user(db, username, password, role)

                self._close_active_dialog()
                self.page.open(ft.SnackBar(ft.Text(f"User '{username}' ({role}) created successfully!"), open=True))
                self.users_table_component.refresh_data_and_ui(self.search_bar.get_value())
            except (ValidationError, DatabaseError) as ex:
                error_text_add.value = str(ex.message if hasattr(ex, 'message') else ex)
                error_text_add.visible = True
            except Exception as ex_general:
                error_text_add.value = f"An unexpected error occurred: {ex_general}"
                error_text_add.visible = True
            if self.page: self.page.update()

        add_user_dialog = create_form_dialog(
            page=self.page,
            title_text="Add New User (Admin/Employee)",
            form_content_column=form_column,
            on_save_callback=_save_new_user_handler,
            on_cancel_callback=self._close_active_dialog,
            min_width=400
        )
        self.page.dialog = add_user_dialog
        self.page.open(self.page.dialog)

    def _handle_table_data_change(self):
        # Placeholder for any actions needed when table data changes
        pass

    def _build_body(self) -> ft.Container:
        user_management_card_content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Account Management", style=ft.TextThemeStyle.HEADLINE_SMALL, weight=ft.FontWeight.BOLD, expand=True),
                        self.search_bar,
                        ft.FilledButton(
                            "Add New User", icon=ft.Icons.PERSON_ADD_ALT_1_ROUNDED,
                            on_click=self._handle_add_user_click,
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                            height=48
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Divider(height=15),
                self.users_table_component,
            ],
            spacing=15,
            expand=True
        )

        TARGET_CARD_MAX_WIDTH = 1000
        page_width_for_calc = self.page.width if self.page.width and self.page.width > 0 else TARGET_CARD_MAX_WIDTH + 40
        card_effective_width = min(TARGET_CARD_MAX_WIDTH, page_width_for_calc - 40)
        card_effective_width = max(card_effective_width, 600)


        user_management_card = ft.Card(
            content=ft.Container(
                content=user_management_card_content,
                padding=20,
                border_radius=ft.border_radius.all(10)
            ),
            elevation=2,
            width=card_effective_width
        )

        return ft.Container(
            content=user_management_card,
            alignment=ft.alignment.top_center,
            padding=20,
            expand=True
        )