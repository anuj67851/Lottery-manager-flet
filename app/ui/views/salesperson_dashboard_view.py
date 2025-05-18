import flet as ft

from app.constants import SALESPERSON_ROLE, ADMIN_ROLE, EMPLOYEE_ROLE, MANAGED_USER_ROLES
from app.core.models import User
from app.core.exceptions import ValidationError, DatabaseError
from app.services.configuration_service import ConfigurationService
from app.services.user_service import UserService
from app.data.database import get_db_session
from app.ui.components.tables.users_table import UsersTable # UsersTable (now PaginatedDataTable)
from app.ui.components.common.appbar_factory import create_appbar # AppBar Factory
from app.ui.components.common.dialog_factory import create_form_dialog # Form Dialog Factory


class SalesPersonDashboardView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user: User, license_status: bool, **params):
        super().__init__(expand=True, padding=20)
        self.page = page
        self.router = router
        self.current_user = current_user
        self.license_service = ConfigurationService()
        self.user_service = UserService()

        self.license_activated = license_status # Initial status from login

        self.page.appbar = create_appbar(
            page=self.page,
            router=self.router,
            title_text="Salesperson Dashboard",
            current_user=self.current_user, # Show current user
            # License status will be shown by the dedicated UI element below
            show_license_status=False,
            show_user_info=True
        )

        # --- UI Components ---
        self.users_table_component = UsersTable(
            page=self.page,
            user_service=self.user_service,
            initial_roles_to_display=[ADMIN_ROLE, EMPLOYEE_ROLE, SALESPERSON_ROLE], # Salesperson sees all
            on_data_changed_callback=self._handle_table_data_change
        )

        self.license_status_label = ft.Text(weight=ft.FontWeight.BOLD)
        self.license_action_button = ft.FilledButton(
            on_click=self._toggle_license,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
        )

        self.content = self._build_body()
        self._update_license_ui_elements() # Initial UI setup for license status
        self.users_table_component.refresh_data_and_ui() # Load user data

    def _get_license_status_string(self) -> str:
        return "Active" if self.license_activated else "Inactive"

    def _update_license_ui_elements(self):
        status_string = self._get_license_status_string()
        self.license_status_label.value = f"License Status: {status_string}"
        self.license_status_label.color = ft.Colors.GREEN_ACCENT_700 if self.license_activated else ft.Colors.RED_ACCENT_700

        if self.license_activated:
            self.license_action_button.text = "Deactivate License"
            self.license_action_button.icon = ft.Icons.KEY_OFF_ROUNDED
            self.license_action_button.tooltip = "Deactivate the current license"
            self.license_action_button.style.bgcolor = ft.Colors.RED_ACCENT_100 # type: ignore
            self.license_action_button.style.color = ft.Colors.RED_ACCENT_700 # type: ignore
        else:
            self.license_action_button.text = "Activate License"
            self.license_action_button.icon = ft.Icons.KEY_ROUNDED
            self.license_action_button.tooltip = "Activate a new license"
            self.license_action_button.style.bgcolor = ft.Colors.GREEN_ACCENT_100 # type: ignore
            self.license_action_button.style.color = ft.Colors.GREEN_ACCENT_700 # type: ignore

        if self.license_status_label.page: self.license_status_label.update()
        if self.license_action_button.page: self.license_action_button.update()
        # No page.update() here, let the caller update the page if necessary

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
        except Exception as ex_general: # Catch any other unexpected error
            self.page.open(
                ft.SnackBar(ft.Text(f"An unexpected error occurred: {ex_general}"), open=True, bgcolor=ft.Colors.ERROR)
            )
        if self.page: self.page.update() # Update page to reflect UI changes

    def _handle_add_user_click(self, e):
        self._open_add_user_dialog()

    def _close_active_dialog(self, e=None):
        if self.page.dialog:
            self.page.close(self.page.dialog) # Use new Flet API
            # self.page.dialog = None # Dialog is removed from page.dialog automatically
            self.page.update()

    def _open_add_user_dialog(self):
        # Form fields for the dialog
        username_field = ft.TextField(label="Username", autofocus=True, border_radius=8)
        password_field = ft.TextField(label="Password", password=True, can_reveal_password=True, border_radius=8)
        confirm_password_field = ft.TextField(label="Confirm Password", password=True, can_reveal_password=True, border_radius=8)
        role_options = [ft.dropdown.Option(role, role.capitalize()) for role in MANAGED_USER_ROLES]
        role_dropdown = ft.Dropdown(label="Role", options=role_options, value=ADMIN_ROLE, border_radius=8) # Default to Admin
        error_text_add = ft.Text(visible=False, color=ft.Colors.RED_700)

        form_column = ft.Column(
            [username_field, password_field, confirm_password_field, role_dropdown, error_text_add],
            tight=True, spacing=15, scroll=ft.ScrollMode.AUTO,
        )

        # Save handler needs access to these fields
        def _save_new_user_handler(e):
            error_text_add.value = ""
            error_text_add.visible = False
            # error_text_add.update() # Update will be handled by page.update()

            username = username_field.value.strip() if username_field.value else ""
            password = password_field.value if password_field.value else ""
            confirm_password = confirm_password_field.value if confirm_password_field.value else ""
            role = role_dropdown.value

            try:
                if not username or not password or not role: # Basic check
                    raise ValidationError("All fields (Username, Password, Role) are required.")
                # More specific validation (e.g., password length) is in UserService

                with get_db_session() as db:
                    self.user_service.create_user(db, username, password, role)

                self._close_active_dialog() # Close dialog first
                self.page.open(ft.SnackBar(ft.Text(f"User '{username}' created successfully!"), open=True))
                self.users_table_component.refresh_data_and_ui() # Refresh table
            except (ValidationError, DatabaseError) as ex:
                error_text_add.value = str(ex.message if hasattr(ex, 'message') else ex)
                error_text_add.visible = True
            except Exception as ex_general:
                error_text_add.value = f"An unexpected error occurred: {ex_general}"
                error_text_add.visible = True

            # error_text_add.update() # Update will be handled by page.update()
            if self.page: self.page.update() # Update dialog content (e.g., show error)

        add_user_dialog = create_form_dialog(
            page=self.page,
            title_text="Add New User",
            form_content_column=form_column,
            on_save_callback=_save_new_user_handler,
            on_cancel_callback=self._close_active_dialog,
            min_width=400 # Ensure dialog is wide enough
        )
        self.page.dialog = add_user_dialog
        self.page.open(self.page.dialog)


    def _handle_table_data_change(self):
        # This callback is from UsersTable (PaginatedDataTable) after its data changes.
        # Could be used to update aggregate counts or other UI elements on this dashboard
        # if there were any that depended on the raw user list.
        # For now, it's a placeholder.
        # print("SalesPersonDashboardView: UsersTable data changed.")
        pass


    def _build_body(self) -> ft.Container:
        welcome_message_text = "Salesperson Controls"
        if self.current_user and self.current_user.username:
            welcome_message_text = f"Welcome, {self.current_user.username} (Salesperson)!"

        license_section = ft.Card(
            elevation=4,
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("License Management", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD),
                        ft.Row(
                            [self.license_status_label, self.license_action_button],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER
                        ),
                    ], spacing=10,
                ),
                padding=20, border_radius=ft.border_radius.all(8), bgcolor=ft.Colors.WHITE70,
            )
        )

        user_management_section = ft.Card(
            elevation=4,
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("User Account Management", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD, expand=True),
                                ft.FilledButton(
                                    "Add New User", icon=ft.Icons.PERSON_ADD_ALT_1_ROUNDED,
                                    on_click=self._handle_add_user_click,
                                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        self.users_table_component, # The UsersTable instance
                    ], spacing=15,
                ),
                padding=20, border_radius=ft.border_radius.all(8), expand=True, bgcolor=ft.Colors.WHITE70,
            ),
            expand=True # Card expands
        )

        # Layout: Center content if page is wide, otherwise let it fill.
        # Using a Column with horizontal_alignment and a max_width container for the content.
        centered_content_column = ft.Column(
            [
                ft.Text(welcome_message_text, style=ft.TextThemeStyle.HEADLINE_MEDIUM, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT), # Spacer
                license_section,
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT), # Spacer
                user_management_section,
            ],
            spacing=20,
            expand=True, # Column itself expands vertically
            # horizontal_alignment=ft.CrossAxisAlignment.CENTER, # Center its children (cards)
            scroll=ft.ScrollMode.ADAPTIVE, # Allow vertical scroll for the whole dashboard content
        )

        return ft.Container( # Outer container to control width and alignment
            content=centered_content_column,
            width=self.page.width * 0.7 if self.page.width and self.page.width > 800 else None, # Max width for content area
            # max_width=800, # Example fixed max width
            alignment=ft.alignment.top_center, # Center the content column on the page
            expand=True,
        )


