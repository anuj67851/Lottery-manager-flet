import flet as ft

from app.constants import SALESPERSON_ROLE, ADMIN_ROLE, EMPLOYEE_ROLE, MANAGED_USER_ROLES
from app.core.models import User
from app.core.exceptions import ValidationError, DatabaseError
from app.services.configuration_service import ConfigurationService
from app.services.user_service import UserService # UserService now has enhanced validation
from app.data.database import get_db_session
from app.ui.components.common.search_bar_component import SearchBarComponent
from app.ui.components.tables.users_table import UsersTable
from app.ui.components.common.appbar_factory import create_appbar
from app.ui.components.common.dialog_factory import create_form_dialog


class SalesPersonDashboardView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user: User, license_status: bool, **params):
        super().__init__(expand=True, padding=20)
        self.page = page
        self.router = router
        self.current_user = current_user
        self.config_service = ConfigurationService()
        self.user_service = UserService()
        self.license_activated = license_status

        self.search_bar = SearchBarComponent(
            on_search_changed=self._on_search_term_changed,
            label="Search Users (Username, Role)",
            expand=True
        )

        self.page.appbar = create_appbar(
            page=self.page,
            router=self.router,
            title_text="Salesperson Dashboard",
            current_user=self.current_user,
            show_license_status=False,
            show_user_info=True
        )

        self.users_table_component = UsersTable(
            page=self.page,
            user_service=self.user_service,
            initial_roles_to_display=[ADMIN_ROLE, EMPLOYEE_ROLE],
            on_data_changed_callback=self._handle_table_data_change,
            current_acting_user=self.current_user,
        )

        self.license_status_label = ft.Text(weight=ft.FontWeight.BOLD)
        self.license_action_button = ft.FilledButton(
            on_click=self._toggle_license,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
        )

        self.content = self._build_body()
        self._update_license_ui_elements()
        self.users_table_component.refresh_data_and_ui()

    def _get_license_status_string(self) -> str:
        return "Active" if self.license_activated else "Inactive"

    def _on_search_term_changed(self, search_term: str):
        self.users_table_component.refresh_data_and_ui(search_term=search_term)

    def _update_license_ui_elements(self):
        self.license_activated = self.config_service.get_license_status()
        status_string = self._get_license_status_string()
        self.license_status_label.value = f"License Status: {status_string}"
        self.license_status_label.color = ft.Colors.GREEN_ACCENT_700 if self.license_activated else ft.Colors.RED_ACCENT_700

        if self.license_activated:
            self.license_action_button.text = "Deactivate License"; self.license_action_button.icon = ft.Icons.KEY_OFF_ROUNDED
            self.license_action_button.tooltip = "Deactivate the current license"
            self.license_action_button.style.bgcolor = ft.Colors.RED_ACCENT_100 # type: ignore
            self.license_action_button.style.color = ft.Colors.RED_ACCENT_700 # type: ignore
        else:
            self.license_action_button.text = "Activate License"; self.license_action_button.icon = ft.Icons.KEY_ROUNDED
            self.license_action_button.tooltip = "Activate a new license"
            self.license_action_button.style.bgcolor = ft.Colors.GREEN_ACCENT_100 # type: ignore
            self.license_action_button.style.color = ft.Colors.GREEN_ACCENT_700 # type: ignore
        if self.license_status_label.page: self.license_status_label.update()
        if self.license_action_button.page: self.license_action_button.update()

    def _toggle_license(self, e):
        new_status_to_set = not self.license_activated
        try:
            self.config_service.set_license_status(new_status_to_set)
            self.license_activated = new_status_to_set
            self._update_license_ui_elements()
            self.page.open(ft.SnackBar(ft.Text(f"License successfully {'activated' if new_status_to_set else 'deactivated'}."), open=True))
        except DatabaseError as ex:
            self.page.open(ft.SnackBar(ft.Text(f"Error updating license: {ex.message}"), open=True, bgcolor=ft.Colors.ERROR))
            self.license_activated = self.config_service.get_license_status(); self._update_license_ui_elements()
        except Exception as ex_general:
            self.page.open(ft.SnackBar(ft.Text(f"An unexpected error occurred: {ex_general}"), open=True, bgcolor=ft.Colors.ERROR))
            self.license_activated = self.config_service.get_license_status(); self._update_license_ui_elements()
        if self.page: self.page.update()

    def _handle_add_user_click(self, e): self._open_add_user_dialog()
    def _close_active_dialog(self, e=None):
        if self.page.dialog: self.page.close(self.page.dialog); self.page.update()

    def _open_add_user_dialog(self):
        username_field = ft.TextField(label="Username", autofocus=True, border_radius=8)
        password_field = ft.TextField(label="Password", password=True, can_reveal_password=True, border_radius=8)
        confirm_password_field = ft.TextField(label="Confirm Password", password=True, can_reveal_password=True, border_radius=8)
        role_options = [ft.dropdown.Option(role, role.capitalize()) for role in MANAGED_USER_ROLES]
        role_dropdown = ft.Dropdown(label="Role", options=role_options, value=EMPLOYEE_ROLE, border_radius=8)
        error_text_add = ft.Text(visible=False, color=ft.Colors.RED_700)
        form_column = ft.Column([username_field, password_field, confirm_password_field, role_dropdown, error_text_add], tight=True, spacing=15, scroll=ft.ScrollMode.AUTO)

        def _save_new_user_handler(e):
            error_text_add.value = ""; error_text_add.visible = False
            username = username_field.value.strip() if username_field.value else ""
            password = password_field.value if password_field.value else ""
            confirm_password = confirm_password_field.value if confirm_password_field.value else ""
            role = role_dropdown.value
            try:
                # UserService.create_user handles all detailed validation
                if not confirm_password: raise ValidationError("Confirm Password field is required.")
                if password != confirm_password: raise ValidationError("Passwords do not match.")
                with get_db_session() as db:
                    self.user_service.create_user(db, username, password, role)
                self._close_active_dialog()
                self.page.open(ft.SnackBar(ft.Text(f"User '{username}' ({role}) created successfully!"), open=True))
                self.users_table_component.refresh_data_and_ui(self.search_bar.get_value())
            except (ValidationError, DatabaseError) as ex:
                error_text_add.value = str(ex.message if hasattr(ex, 'message') else ex); error_text_add.visible = True
            except Exception as ex_general:
                error_text_add.value = f"An unexpected error occurred: {ex_general}"; error_text_add.visible = True
            if error_text_add.page: error_text_add.update() # Only update error text if it's visible

        add_user_dialog = create_form_dialog(page=self.page, title_text="Add New User (Admin/Employee)", form_content_column=form_column, on_save_callback=_save_new_user_handler, on_cancel_callback=self._close_active_dialog, min_width=400)
        self.page.dialog = add_user_dialog; self.page.open(self.page.dialog)

    def _handle_table_data_change(self): pass

    def _build_body(self) -> ft.Container:
        # Layout remains largely the same, UserService calls now have better validation.
        welcome_message_text = "Salesperson Controls"
        if self.current_user and self.current_user.username:
            welcome_message_text = f"Welcome, {self.current_user.username} (Salesperson)!"
        license_section = ft.Card(elevation=4, content=ft.Container(content=ft.Column([ft.Text("License Management", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD), ft.Row([self.license_status_label, self.license_action_button], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)], spacing=10), padding=20, border_radius=ft.border_radius.all(8)))
        user_management_section = ft.Card(elevation=4, content=ft.Container(content=ft.Column([ft.Row([ft.Text("User Account Management (Admins & Employees)", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD, expand=True), self.search_bar, ft.FilledButton("Add New User", icon=ft.Icons.PERSON_ADD_ALT_1_ROUNDED, on_click=self._handle_add_user_click, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER), ft.Divider(height=10, color=ft.Colors.TRANSPARENT), self.users_table_component], spacing=15), padding=20, border_radius=ft.border_radius.all(8), expand=True), expand=True)
        centered_content_column = ft.Column([ft.Text(welcome_message_text, style=ft.TextThemeStyle.HEADLINE_MEDIUM, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER), ft.Divider(height=20, color=ft.Colors.TRANSPARENT), license_section, ft.Divider(height=20, color=ft.Colors.TRANSPARENT), user_management_section], spacing=20, expand=True, scroll=ft.ScrollMode.ADAPTIVE, width=1000)
        return ft.Container(content=centered_content_column, alignment=ft.alignment.top_center, expand=True)