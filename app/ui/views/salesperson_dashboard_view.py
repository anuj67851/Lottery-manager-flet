import flet as ft

from app.constants import LOGIN_ROUTE, SALESPERSON_ROLE, ADMIN_ROLE, EMPLOYEE_ROLE, MANAGED_USER_ROLES
from app.core.models import User
from app.core.exceptions import ValidationError, DatabaseError
from app.services.license_service import LicenseService
from app.services.user_service import UserService
from app.data.database import get_db_session
from app.ui.components.tables.users_table import UsersTable


class SalesPersonDashboardView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user: User, license_status: bool, **params):
        super().__init__(expand=True, padding=20) # Add padding to the main container
        self.page = page
        self.router = router
        self.current_user = current_user
        self.license_service = LicenseService()
        self.user_service = UserService()

        self.license_activated = license_status

        # --- UI Components ---
        self.users_table_component = UsersTable(
            page=self.page,
            user_service=self.user_service,
            initial_roles_to_display=[SALESPERSON_ROLE, ADMIN_ROLE, EMPLOYEE_ROLE], # Show all for salesperson
            on_data_changed=self._handle_table_data_change # Optional: if other parts of this view need to react
        )

        self.license_status_label = ft.Text(weight=ft.FontWeight.BOLD)
        self.license_action_button = ft.FilledButton(
            on_click=self._toggle_license,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
        )

        self.page.appbar = self._build_appbar()
        self.content = self._build_body()
        self._update_license_ui_elements() # Initial UI setup for license

    def _build_appbar(self):
        return ft.AppBar(
            title=ft.Text("Salesperson Dashboard"),
            bgcolor=ft.Colors.BLUE_700, # Kept original color
            color=ft.Colors.WHITE,      # Kept original color
            actions=[
                ft.IconButton(
                    icon=ft.Icons.LOGOUT,
                    tooltip="Logout",
                    icon_color=ft.Colors.WHITE, # Kept original color
                    on_click=self.logout,
                ),
            ],
        )

    def _get_license_status_string(self):
        return "Active" if self.license_activated else "Inactive"

    def _update_license_ui_elements(self):
        status_string = self._get_license_status_string()
        self.license_status_label.value = f"License Status: {status_string}"
        self.license_status_label.color = ft.Colors.GREEN_ACCENT_700 if self.license_activated else ft.Colors.RED_ACCENT_700

        if self.license_activated:
            self.license_action_button.text = "Deactivate License"
            self.license_action_button.icon = ft.Icons.KEY_OFF_ROUNDED # Kept original icon
            self.license_action_button.tooltip = "Deactivate the current license"
            self.license_action_button.style.bgcolor = ft.Colors.RED_ACCENT_100
            self.license_action_button.style.color = ft.Colors.RED_ACCENT_700

        else:
            self.license_action_button.text = "Activate License"
            self.license_action_button.icon = ft.Icons.KEY_ROUNDED # Kept original icon
            self.license_action_button.tooltip = "Activate a new license"
            self.license_action_button.style.bgcolor = ft.Colors.GREEN_ACCENT_100
            self.license_action_button.style.color = ft.Colors.GREEN_ACCENT_700


        if self.license_status_label.page: self.license_status_label.update()
        if self.license_action_button.page: self.license_action_button.update()
        if self.page: self.page.update()


    def _toggle_license(self, e):
        new_status = not self.license_activated
        try:
            with get_db_session() as db:
                self.license_service.set_license_status(db, new_status)
            self.license_activated = new_status # Update state only on success
            self._update_license_ui_elements()
            self.page.open(
                ft.SnackBar(ft.Text(f"License successfully {'activated' if new_status else 'deactivated'}."), open=True)
            )
        except DatabaseError as ex:
            self.page.open(
                ft.SnackBar(ft.Text(f"Error updating license: {ex.message}"), open=True, bgcolor=ft.Colors.ERROR)
            )
        except Exception as ex_general:
            self.page.open(
                ft.SnackBar(ft.Text(f"An unexpected error occurred: {ex_general}"), open=True, bgcolor=ft.Colors.ERROR)
            )


    def _handle_add_user_click(self, e):
        self._open_add_user_dialog()

    def _open_add_user_dialog(self):
        def _save_new_user(e):
            error_text_add.value = ""
            error_text_add.visible = False

            username = username_field.value.strip()
            password = password_field.value
            confirm_password = confirm_password_field.value
            role = role_dropdown.value

            if not username or not password or not role:
                error_text_add.value = "All fields are required."
                error_text_add.visible = True
                error_text_add.update()
                self.page.update()
                return
            if len(password) < 6:
                error_text_add.value = "Password must be at least 6 characters long."
                error_text_add.visible = True
                error_text_add.update()
                self.page.update()
                return
            if password != confirm_password:
                error_text_add.value = "Passwords do not match."
                error_text_add.visible = True
                error_text_add.update()
                self.page.update()
                return

            try:
                with get_db_session() as db:
                    self.user_service.create_user(db, username, password, role)
                self.page.open(ft.SnackBar(ft.Text(f"User '{username}' created successfully!"), open=True))
                self._close_dialog()
                self.users_table_component.refresh_data() # Refresh the users table
            except (ValidationError, DatabaseError) as ex:
                error_text_add.value = str(ex)
                error_text_add.visible = True
            except Exception as ex_general:
                error_text_add.value = f"An unexpected error occurred: {ex_general}"
                error_text_add.visible = True

            error_text_add.update()
            self.page.update()

        username_field = ft.TextField(label="Username", autofocus=True, border_radius=8, on_submit=_save_new_user)
        password_field = ft.TextField(label="Password", password=True, can_reveal_password=True, border_radius=8, on_submit=_save_new_user)
        confirm_password_field = ft.TextField(label="Confirm Password", password=True, can_reveal_password=True, border_radius=8, on_submit=_save_new_user)

        role_options = [ft.dropdown.Option(role, role.capitalize()) for role in MANAGED_USER_ROLES]
        role_dropdown = ft.Dropdown(label="Role", options=role_options, value=ADMIN_ROLE, border_radius=8)

        error_text_add = ft.Text(visible=False, color=ft.Colors.RED_700)

        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Add New User"),
            content=ft.Container(
                ft.Column(
                    [
                        username_field,
                        password_field,
                        confirm_password_field,
                        role_dropdown,
                        error_text_add
                    ],
                    tight=True,
                    spacing=15,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=ft.padding.symmetric(horizontal=24, vertical=20),
                border_radius=8,
                width=self.page.width / 3.5,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=self._close_dialog, style=ft.ButtonStyle(color=ft.Colors.BLUE_GREY)),
                ft.FilledButton("Create User", on_click=_save_new_user),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(self.page.dialog)

    def _close_dialog(self, e=None):
        if self.page.dialog:
            self.page.close(self.page.dialog)
            self.page.dialog = None
            self.page.update()

    def _handle_table_data_change(self):
        # Placeholder if this view needs to react to table changes directly
        # For example, update a count of users displayed elsewhere on this page.
        pass


    def _build_body(self):
        welcome_message_text = "Welcome, Salesperson!"
        if self.current_user and self.current_user.username:
            welcome_message_text = f"Welcome, {self.current_user.username} (Salesperson)!"

        # License Section Card
        license_section = ft.Card(
            elevation=4, # Add some shadow
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("License Management", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD),
                        ft.Row(
                            [self.license_status_label, self.license_action_button],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN, # Space out label and button
                            vertical_alignment=ft.CrossAxisAlignment.CENTER
                        ),
                    ],
                    spacing=10,
                ),
                padding=20,
                border_radius=8,
            )
        )

        # User Management Section Card
        user_management_section = ft.Card(
            elevation=4,
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("User Management", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD, expand=True),
                                ft.FilledButton(
                                    "Add New User",
                                    icon=ft.Icons.PERSON_ADD_ALT_1_ROUNDED, # Kept icon
                                    on_click=self._handle_add_user_click,
                                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT), # Spacer
                        self.users_table_component, # The UsersTable instance
                    ],
                    spacing=15,
                ),
                padding=20,
                border_radius=8,
                expand=True, # Allow user management to take more space
            ),
            expand=True # Card expands
        )

        return ft.Column(
            [
                ft.Text(welcome_message_text, style=ft.TextThemeStyle.HEADLINE_MEDIUM, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                license_section,
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                user_management_section,
            ],
            spacing=20, # Spacing between major sections
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER, # Stretch cards to fill width
            scroll=ft.ScrollMode.ADAPTIVE, # Add scroll if content overflows
            width=self.page.width / 2.5,

        )

    def logout(self, e):
        self.current_user = None
        # self.page.appbar = None # Router will handle this
        self.router.navigate_to(LOGIN_ROUTE)