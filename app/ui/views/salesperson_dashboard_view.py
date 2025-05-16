import flet as ft
from app.constants import LOGIN_ROUTE, SALESPERSON_ROLE, ADMIN_ROLE, EMPLOYEE_ROLE
from app.core.models import User
from app.ui.components.tables.users_table import UsersTable # Assuming UsersTable is in this path


class SalesPersonDashboardView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user: User = None, **params):
        super().__init__(expand=True)
        self.page = page
        self.router = router
        self.current_user = current_user

        # --- State for License ---
        self.license_activated = False  # Initial license state (e.g., fetch from a backend)

        # --- UI Components ---
        self.users_table = UsersTable(
            self.page,
            user_roles=[SALESPERSON_ROLE, ADMIN_ROLE, EMPLOYEE_ROLE],
            # Callbacks for edit/delete would be handled by UsersTable or passed here
        )

        self.license_status_label = ft.Text()
        self.license_action_button = ft.ElevatedButton(on_click=self._toggle_license)

        self.page.appbar = self._build_appbar()
        self.content = self._build_body()
        self._update_license_controls()

    def _build_appbar(self):
        return ft.AppBar(
            title=ft.Text("Sales person Dashboard"),
            bgcolor=ft.Colors.BLUE_700,
            color=ft.Colors.WHITE,
            actions=[
                ft.IconButton(
                    icon=ft.Icons.LOGOUT,
                    tooltip="Logout",
                    icon_color=ft.Colors.WHITE,
                    on_click=self.logout,
                ),
            ],
        )

    def _get_license_status_string(self):
        return "Active" if self.license_activated else "Inactive"

    def _update_license_controls(self):
        status_string = self._get_license_status_string()
        self.license_status_label.value = f"License Status: {status_string}"
        if self.license_activated:
            self.license_action_button.text = "Deactivate License"
            self.license_action_button.icon = ft.Icons.KEY_OFF
            self.license_action_button.tooltip = "Deactivate the current license"
        else:
            self.license_action_button.text = "Activate License"
            self.license_action_button.icon = ft.Icons.KEY
            self.license_action_button.tooltip = "Activate a new license"

        if self.license_status_label.page:
            self.license_status_label.update()
        if self.license_action_button.page:
            self.license_action_button.update()

    def _toggle_license(self, e):
        self.license_activated = not self.license_activated
        print(f"License toggled. New status: {'Active' if self.license_activated else 'Inactive'}")
        self._update_license_controls()

    def _handle_add_user(self, e):
        print("Add User button clicked")
        # Implement logic for adding a user

    def _build_body(self):
        welcome_message_text = "Welcome, Sales person!"
        if self.current_user and self.current_user.username:
            welcome_message_text = f"Welcome, {self.current_user.username} (Sales Person)!"

        # License Section
        license_section = ft.Container(
            content=ft.Column(
                [
                    ft.Text("License Management", weight=ft.FontWeight.BOLD, size=20),
                    self.license_status_label,
                    self.license_action_button,
                ],
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.START, # Aligns this section's content to the start
            ),
            padding=ft.padding.only(bottom=20),
        )

        # User Management Section - MODIFIED
        user_management_section = ft.Container(
            content=ft.Column(
                controls=[
                    # Header Row: "Manage Users" text and "Add User" button
                    ft.Row(
                        controls=[
                            ft.Text("Manage Users", weight=ft.FontWeight.BOLD, size=20),
                            ft.ElevatedButton(
                                "Add User",
                                icon=ft.Icons.ADD,
                                on_click=self._handle_add_user,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER, # Center Text and Button together as a block
                        spacing=25, # Space between the text and the button
                    ),
                    # The UsersTable instance
                    self.users_table,
                ],
                spacing=15, # Spacing between the Header Row and the UsersTable
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, # Centers the Header Row and the UsersTable
                expand=True,
            ),
            expand=True,
        )

        return ft.Column(
            [
                ft.Text(welcome_message_text, size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Divider(height=20), # Visual spacer after welcome message
                license_section,
                ft.Divider(height=1, color=ft.Colors.BLACK26), # Visual separator
                user_management_section,
            ],
            spacing=15,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER, # Center all main sections on the page
        )

    def logout(self, e):
        self.current_user = None
        self.page.appbar = None
        self.router.navigate_to(LOGIN_ROUTE)
