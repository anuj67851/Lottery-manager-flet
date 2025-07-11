from typing import List, Callable, Optional, Type, Dict, Any
import flet as ft
import datetime

from app.constants import ADMIN_ROLE, EMPLOYEE_ROLE, SALESPERSON_ROLE, MANAGED_USER_ROLES, ALL_USER_ROLES
from app.core.exceptions import WidgetError, ValidationError, DatabaseError, UserNotFoundError
from app.core.models import User
from app.services.user_service import UserService
from app.data.database import get_db_session
from app.ui.components.common.paginated_data_table import PaginatedDataTable # Import base class
from app.ui.components.common.dialog_factory import create_confirmation_dialog, create_form_dialog # Import dialog factory

class UsersTable(PaginatedDataTable[User]):
    def __init__(self, page: ft.Page, user_service: UserService,
                 initial_roles_to_display: List[str], # Used for initial data fetch query
                 current_acting_user: User, # User performing the actions
                 on_data_changed_callback: Optional[Callable[[], None]] = None): # Renamed for clarity

        self.user_service = user_service
        self.initial_roles_to_display = initial_roles_to_display
        self.current_acting_user = current_acting_user # Store the acting user
        if not self.initial_roles_to_display:
            raise WidgetError("User roles must be provided for UsersTable.")
        self._on_data_changed_callback = on_data_changed_callback
        self.current_action_user: Optional[User] = None # For dialog context

        column_definitions: List[Dict[str, Any]] = [
            {"key": "id", "label": "ID", "sortable": True, "numeric": False, "searchable": False,
             "display_formatter": lambda val: ft.Text(str(val))},
            {"key": "username", "label": "Username", "sortable": True, "numeric": False, "searchable": True,
             "display_formatter": lambda val: ft.Text(str(val))},
            {"key": "role", "label": "Role", "sortable": True, "numeric": False, "searchable": True, # Role can be searched
             "display_formatter": lambda val: ft.Text(str(val).capitalize())},
            {"key": "created_date", "label": "Created Date (YYYY-MM-DD)", "sortable": True, "numeric": False, "searchable": False,
             "display_formatter": lambda val_date: ft.Text(val_date.strftime("%Y-%m-%d %H:%M") if val_date else "")},
            {"key": "is_active", "label": "Is Active?", "sortable": True, "numeric": False, "searchable": False, # Not directly searchable as bool
             "display_formatter": lambda val_bool: ft.Text("Yes" if val_bool else "No", color=ft.Colors.GREEN if val_bool else ft.Colors.RED)},
        ]

        super().__init__(
            page=page,
            fetch_all_data_func=self._fetch_users_data,
            column_definitions=column_definitions,
            action_cell_builder=self._build_action_cell,
            rows_per_page=10, # Users table might show more, adjust as needed
            initial_sort_key="id",
            initial_sort_ascending=True,
            show_pagination=True, # UsersTable did not have pagination, keeping that look
            default_search_enabled=True, # UsersTable did not have search, keeping that look
        )

    def _fetch_users_data(self, db_session) -> List[User]:
        """Implements data fetching for users based on initial roles."""
        # If self.initial_roles_to_display is empty or ALL, fetch all users
        if not self.initial_roles_to_display or set(self.initial_roles_to_display) == set(ALL_USER_ROLES):
            return self.user_service.get_all_users(db_session)
        return self.user_service.get_users_by_roles(db_session, roles=self.initial_roles_to_display)

    def _build_action_cell(self, user: User, table_instance: PaginatedDataTable) -> ft.DataCell:
        actions_controls = []
        edit_button = ft.IconButton(
            icon=ft.Icons.EDIT_ROUNDED, tooltip="Edit user", icon_color=ft.Colors.PRIMARY,
            on_click=lambda e, u=user: self._open_edit_user_dialog(u)
        )
        actions_controls.append(edit_button)

        # Restriction: Salesperson users cannot be deactivated/reactivated from this generic table
        # Also, current acting user cannot deactivate/reactivate themselves.
        can_toggle_active_status = True
        if user.role == SALESPERSON_ROLE:
            can_toggle_active_status = False
        if self.current_acting_user and self.current_acting_user.id == user.id:
            can_toggle_active_status = False


        if can_toggle_active_status:
            if user.is_active:
                deactivate_button = ft.IconButton(
                    icon=ft.Icons.DESKTOP_ACCESS_DISABLED_OUTLINED, tooltip="Deactivate user", icon_color=ft.Colors.RED_ACCENT_700,
                    on_click=lambda e, u=user: self._confirm_deactivate_user_dialog(u)
                )
                actions_controls.append(deactivate_button)
            else:
                reactivate_button = ft.IconButton(
                    icon=ft.Icons.DESKTOP_WINDOWS_ROUNDED, tooltip="Reactivate user", icon_color=ft.Colors.GREEN_ACCENT_700,
                    on_click=lambda e, u=user: self._confirm_reactivate_user_dialog(u)
                )
                actions_controls.append(reactivate_button)

        return ft.DataCell(ft.Row(actions_controls, spacing=0, alignment=ft.MainAxisAlignment.END))

    def _filter_and_sort_displayed_data(self, search_term: str = ""):
        super()._filter_and_sort_displayed_data(search_term)
        if self._on_data_changed_callback:
            self._on_data_changed_callback()

    # --- Dialog handling specific to UsersTable ---
    def _close_dialog_and_refresh_users(self, dialog_to_close: Optional[ft.AlertDialog]=None, success_message: Optional[str]=None):
        if dialog_to_close and self.page.dialog == dialog_to_close:
            self.page.close(dialog_to_close)
        if success_message and self.page:
            self.page.open(ft.SnackBar(ft.Text(success_message), open=True))
        self.refresh_data_and_ui() # Refresh user data

    # --- Edit User Dialog (Complex Form Dialog - kept mostly as is but uses factory for shell) ---
    def _open_edit_user_dialog(self, user_to_edit: User): # Renamed user to user_to_edit
        self.current_action_user = user_to_edit

        # Determine if password fields should be disabled
        disable_password_fields = False
        password_restriction_message = ""
        if (self.current_acting_user and self.current_acting_user.role == ADMIN_ROLE and
                user_to_edit.role == ADMIN_ROLE and self.current_acting_user.id != user_to_edit.id):
            disable_password_fields = True
            password_restriction_message = "Admin cannot change another admin's password."

        # Form fields
        username_field = ft.TextField(label="Username", value=user_to_edit.username, disabled=True)
        role_options = [ft.dropdown.Option(role, role.capitalize()) for role in MANAGED_USER_ROLES]
        role_dropdown = ft.Dropdown(
            label="Role", options=role_options, value=user_to_edit.role,
            disabled=(user_to_edit.role == SALESPERSON_ROLE or # Salesperson role cannot be changed
                      (self.current_acting_user and self.current_acting_user.id == user_to_edit.id and user_to_edit.role == ADMIN_ROLE)) # Admin cannot change own role if they are the one being edited
        )
        password_field = ft.TextField(
            label="New Password (optional)", password=True, can_reveal_password=True,
            disabled=disable_password_fields
        )
        confirm_password_field = ft.TextField(
            label="Confirm New Password", password=True, can_reveal_password=True,
            disabled=disable_password_fields
        )
        error_text_edit = ft.Text(visible=False, color=ft.Colors.RED_700)

        form_controls = [
            username_field, role_dropdown,
            ft.Text("Leave password fields blank to keep current password." if not disable_password_fields else password_restriction_message,
                    italic=True, size=12, color=ft.Colors.ORANGE_ACCENT_700 if disable_password_fields else ft.Colors.ON_SURFACE_VARIANT),
            password_field, confirm_password_field, error_text_edit,
        ]

        form_column = ft.Column(
            form_controls,
            tight=True, spacing=15, width=380, # Adjusted width slightly for message
            scroll=ft.ScrollMode.AUTO
        )

        # Save handler needs access to these fields
        def _save_edits_handler(e):
            self._save_user_edits(role_dropdown, password_field, confirm_password_field, error_text_edit, disable_password_fields)

        edit_dialog = create_form_dialog(
            page=self.page,
            title_text=f"Edit User: {user_to_edit.username}",
            form_content_column=form_column,
            on_save_callback=_save_edits_handler,
            on_cancel_callback=lambda ev: self._close_dialog_and_refresh_users(self.page.dialog) # type: ignore
        )
        self.page.dialog = edit_dialog
        self.page.open(self.page.dialog)


    def _save_user_edits(self, role_field: ft.Dropdown, password_field: ft.TextField,
                         confirm_password_field: ft.TextField, error_text_edit: ft.Text,
                         password_fields_disabled: bool):
        if not self.current_action_user: return

        error_text_edit.value = ""
        error_text_edit.visible = False

        new_role = role_field.value
        new_password = None
        if not password_fields_disabled:
            new_password = password_field.value if password_field.value else None
            confirm_new_password = confirm_password_field.value

            # Password validation only if not disabled and new password provided
            if new_password:
                if len(new_password) < 6:
                    raise ValidationError("New password must be at least 6 characters.")
                if new_password != confirm_new_password:
                    raise ValidationError("New passwords do not match.")
        try:
            with get_db_session() as db:
                self.user_service.update_user(
                    db, user_id=self.current_action_user.id, # type: ignore
                    password=new_password, role=new_role
                    # Note: is_active is handled by separate deactivate/reactivate actions
                )
            self._close_dialog_and_refresh_users(self.page.dialog, "User details updated successfully.") # type: ignore
        except (ValidationError, DatabaseError, UserNotFoundError) as ex:
            error_text_edit.value = str(ex.message if hasattr(ex, 'message') else ex)
            error_text_edit.visible = True
        except Exception as ex_general:
            error_text_edit.value = f"An unexpected error occurred: {ex_general}"
            error_text_edit.visible = True

        if self.page: self.page.update() # Update dialog with error or after closing


    # --- Confirmation Dialogs (Deactivate/Reactivate - use DialogFactory) ---
    def _confirm_deactivate_user_dialog(self, user: User):
        self.current_action_user = user
        content = ft.Text(f"Are you sure you want to deactivate user '{user.username}' (ID: {user.id})?")
        dialog = create_confirmation_dialog(
            title_text="Confirm Deactivate", title_color=ft.Colors.RED_700, content_control=content,
            on_confirm=self._handle_deactivate_confirmed,
            on_cancel=lambda e: self._close_dialog_and_refresh_users(self.page.dialog), # type: ignore
            confirm_button_text="Deactivate User",
            confirm_button_style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE)
        )
        self.page.dialog = dialog
        self.page.open(self.page.dialog)

    def _handle_deactivate_confirmed(self, e=None):
        if not self.current_action_user: return
        user_to_deactivate = self.current_action_user
        current_dialog = self.page.dialog
        try:
            with get_db_session() as db:
                self.user_service.deactivate_user(db, user_id=user_to_deactivate.id) # type: ignore
            self._close_dialog_and_refresh_users(current_dialog, f"User '{user_to_deactivate.username}' deactivated.")
        except (UserNotFoundError, DatabaseError, ValidationError) as ex: # Added ValidationError
            self.show_error_snackbar(str(ex.message if hasattr(ex, 'message') else ex))
            self._close_dialog_and_refresh_users(current_dialog)
        except Exception as ex_general:
            self.show_error_snackbar(f"An unexpected error: {ex_general}")
            self._close_dialog_and_refresh_users(current_dialog)
        finally: self.current_action_user = None


    def _confirm_reactivate_user_dialog(self, user: User):
        self.current_action_user = user
        content = ft.Text(f"Are you sure you want to reactivate user '{user.username}' (ID: {user.id})?")
        dialog = create_confirmation_dialog(
            title_text="Confirm Reactivate", title_color=ft.Colors.GREEN_700, content_control=content,
            on_confirm=self._handle_reactivate_confirmed,
            on_cancel=lambda e: self._close_dialog_and_refresh_users(self.page.dialog), # type: ignore
            confirm_button_text="Reactivate User",
            confirm_button_style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)
        )
        self.page.dialog = dialog
        self.page.open(self.page.dialog)

    def _handle_reactivate_confirmed(self, e=None):
        if not self.current_action_user: return
        user_to_reactivate = self.current_action_user
        current_dialog = self.page.dialog
        try:
            with get_db_session() as db:
                self.user_service.reactivate_user(db, user_id=user_to_reactivate.id) # type: ignore
            self._close_dialog_and_refresh_users(current_dialog, f"User '{user_to_reactivate.username}' reactivated.")
        except (UserNotFoundError, DatabaseError, ValidationError) as ex: # Added ValidationError
            self.show_error_snackbar(str(ex.message if hasattr(ex, 'message') else ex))
            self._close_dialog_and_refresh_users(current_dialog)
        except Exception as ex_general:
            self.show_error_snackbar(f"An unexpected error: {ex_general}")
            self._close_dialog_and_refresh_users(current_dialog)
        finally: self.current_action_user = None