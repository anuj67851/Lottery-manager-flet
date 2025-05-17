from typing import List, Callable, Optional, Type
import flet as ft

from app.constants import ADMIN_ROLE, EMPLOYEE_ROLE, SALESPERSON_ROLE, MANAGED_USER_ROLES
from app.core.exceptions import WidgetError, ValidationError, DatabaseError, UserNotFoundError
from app.core.models import User
from app.services.user_service import UserService
from app.data.database import get_db_session

class UsersTable(ft.Container):
    def __init__(self, page: ft.Page, user_service: UserService, initial_roles_to_display: List[str],
                 on_data_changed: Optional[Callable[[], None]] = None):
        super().__init__(expand=True, padding=ft.padding.symmetric(horizontal=10))
        self.page = page
        self.user_service = user_service
        self.initial_roles_to_display = initial_roles_to_display
        self.on_data_changed = on_data_changed # Callback to notify parent of changes

        if not self.initial_roles_to_display:
            raise WidgetError("User roles must be provided for UsersTable.")

        self.users: List[Type[User]] = []
        self.datatable = ft.DataTable(
            columns=[], # Will be set in _build_layout
            rows=[],    # Will be set in _build_layout
            column_spacing=20,
            expand=True,
            # width=700 # Example width, adjust as needed
        )
        self.content = self._build_layout()
        self.refresh_data() # Load initial data

    def _build_layout(self) -> ft.Column:
        return ft.Column(
            controls=[
                self.datatable
            ],
            expand=True,
            # horizontal_alignment=ft.CrossAxisAlignment.CENTER # Center the table if it's narrower than container
        )

    def refresh_data(self):
        try:
            with get_db_session() as db:
                self.users = self.user_service.get_users_by_roles(db, roles=self.initial_roles_to_display)
            self._update_datatable()
            if self.on_data_changed:
                self.on_data_changed()
        except Exception as e:
            print(f"Error refreshing users table data: {e}")
            if self.page:
                self.page.open(ft.SnackBar(ft.Text(f"Error loading users: {e}"), open=True, bgcolor=ft.Colors.ERROR))


    def _update_datatable(self):
        self.datatable.columns = [
            ft.DataColumn(ft.Text("ID", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Username", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Role", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Created Date", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.BOLD), numeric=True), # Align actions to the right
        ]

        rows = []
        for user in self.users:
            actions_controls = []

            edit_button = ft.IconButton(
                icon=ft.Icons.EDIT_ROUNDED,
                tooltip="Edit user",
                icon_color=ft.Colors.PRIMARY,
                on_click=lambda e, u=user: self._open_edit_user_dialog(u)
            )
            actions_controls.append(edit_button)

            # Salespersons cannot be deleted via this interface by other salespersons
            # and their role cannot be changed from 'salesperson'.
            # Only allow delete for non-salesperson roles.
            if user.role != SALESPERSON_ROLE:
                delete_button = ft.IconButton(
                    icon=ft.Icons.DELETE_FOREVER_ROUNDED,
                    tooltip="Delete user",
                    icon_color=ft.Colors.RED_ACCENT_700,
                    on_click=lambda e, u=user: self._confirm_delete_user_dialog(u)
                )
                actions_controls.append(delete_button)

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(user.id))),
                        ft.DataCell(ft.Text(user.username)),
                        ft.DataCell(ft.Text(user.role.capitalize())),
                        ft.DataCell(ft.Text(user.created_date.strftime("%Y-%m-%d %H:%M"))),
                        ft.DataCell(ft.Row(actions_controls, spacing=0, alignment=ft.MainAxisAlignment.END)),
                    ]
                )
            )
        self.datatable.rows = rows
        if self.page: # Ensure table updates if it's already on page
            self.page.update()


    def _close_dialog(self, e=None):
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()
            self.page.dialog = None # Clear dialog from page state

    def _open_edit_user_dialog(self, user: User):
        self.current_edit_user_id = user.id # Store ID for update

        username_field = ft.TextField(label="Username", value=user.username, disabled=True) # Username typically not editable

        role_options = [ft.dropdown.Option(role, role.capitalize()) for role in MANAGED_USER_ROLES]
        role_field = ft.Dropdown(
            label="Role",
            options=role_options,
            value=user.role,
            disabled=(user.role == SALESPERSON_ROLE) # Salesperson role cannot be changed
        )

        password_field = ft.TextField(label="New Password (optional)", password=True, can_reveal_password=True)
        confirm_password_field = ft.TextField(label="Confirm New Password", password=True, can_reveal_password=True)

        error_text_edit = ft.Text(visible=False, color=ft.Colors.RED_700)

        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Edit User: {user.username}"),
            content=ft.Column(
                [
                    username_field,
                    role_field,
                    ft.Text("Leave password fields blank to keep current password.", italic=True, size=12),
                    password_field,
                    confirm_password_field,
                    error_text_edit,
                ],
                tight=True,
                spacing=15,
                width=350, # Adjust width as needed
                height=350, # Adjust height for content
                scroll=ft.ScrollMode.AUTO
            ),
            actions=[
                ft.TextButton("Cancel", on_click=self._close_dialog, style=ft.ButtonStyle(color=ft.Colors.BLUE_GREY)),
                ft.FilledButton("Save Changes", on_click=lambda e: self._save_user_edits(
                    role_field, password_field, confirm_password_field, error_text_edit
                )),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog.open = True
        self.page.update()

    def _save_user_edits(self, role_field: ft.Dropdown, password_field: ft.TextField,
                         confirm_password_field: ft.TextField, error_text_edit: ft.Text):
        error_text_edit.value = ""
        error_text_edit.visible = False

        new_role = role_field.value
        new_password = password_field.value
        confirm_new_password = confirm_password_field.value

        if new_password: # If password is being changed
            if len(new_password) < 6:
                error_text_edit.value = "New password must be at least 6 characters."
                error_text_edit.visible = True
                error_text_edit.update()
                self.page.update()
                return
            if new_password != confirm_new_password:
                error_text_edit.value = "New passwords do not match."
                error_text_edit.visible = True
                error_text_edit.update()
                self.page.update()
                return
        else: # Password not being changed
            new_password = None # Pass None to service layer

        try:
            with get_db_session() as db:
                self.user_service.update_user(
                    db,
                    user_id=self.current_edit_user_id,
                    # username=None, # Assuming username is not changed here
                    password=new_password,
                    role=new_role
                )
            self.page.show_snack_bar(ft.SnackBar(ft.Text(f"User details updated successfully."), open=True))
            self._close_dialog()
            self.refresh_data() # Refresh table
        except (ValidationError, DatabaseError, UserNotFoundError) as ex:
            error_text_edit.value = str(ex)
            error_text_edit.visible = True
        except Exception as ex_general:
            error_text_edit.value = f"An unexpected error occurred: {ex_general}"
            error_text_edit.visible = True

        error_text_edit.update()
        self.page.update()


    def _confirm_delete_user_dialog(self, user: User):
        self.current_delete_user_id = user.id # Store ID for deletion

        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Delete", color=ft.Colors.RED_700),
            content=ft.Text(f"Are you sure you want to permanently delete user '{user.username}' (ID: {user.id})? This action cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=self._close_dialog),
                ft.FilledButton("Delete User", style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE),
                                on_click=self._handle_delete_confirmed),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog.open = True
        self.page.update()

    def _handle_delete_confirmed(self, e=None):
        try:
            with get_db_session() as db:
                self.user_service.delete_user(db, user_id=self.current_delete_user_id)
            self.page.open(ft.SnackBar(ft.Text(f"User (ID: {self.current_delete_user_id}) deleted successfully."), open=True))
            self._close_dialog()
            self.refresh_data() # Refresh table
        except UserNotFoundError as ex:
            self._close_dialog() # Close confirmation dialog
            self.page.open(ft.SnackBar(ft.Text(str(ex)), open=True, bgcolor=ft.Colors.ERROR))
            self.refresh_data() # Refresh table to reflect that user might already be gone
        except DatabaseError as ex:
            self._close_dialog()
            self.page.open(ft.SnackBar(ft.Text(f"Error deleting user: {ex}"), open=True, bgcolor=ft.Colors.ERROR))
        except Exception as ex_general:
            self._close_dialog()
            self.page.open(ft.SnackBar(ft.Text(f"An unexpected error occurred: {ex_general}"), open=True, bgcolor=ft.Colors.ERROR))
