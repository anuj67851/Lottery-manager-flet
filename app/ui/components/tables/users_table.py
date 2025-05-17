from typing import List

import flet as ft

from app.constants import ADMIN_ROLE, EMPLOYEE_ROLE, SALESPERSON_ROLE
from app.core.exceptions import WidgetError
from app.core.models import User
from app.data.crud_users import get_users_by_roles
from app.data.database import get_db_session


class UsersTable(ft.Container):
    def __init__(self, page: ft.Page, user_roles, **params):
        super().__init__()
        if user_roles is None:
            raise WidgetError("User roles must be provided for UsersTable.")
        elif ADMIN_ROLE not in user_roles and EMPLOYEE_ROLE not in user_roles and SALESPERSON_ROLE not in user_roles:
            raise WidgetError("User roles must contain at least one of the following roles: ADMIN, EMPLOYEE, SALESPERSON.")

        with get_db_session() as db:
            self.users = get_users_by_roles(db, roles=user_roles)

        self.page = page
        self.content = self._build_layout()

    def _build_layout(self):
        return ft.Column(
            controls=[
                self._create_users_table(self.users),
            ],
        )

    def _create_users_table(self, users: List[User]):
        columns = [
            ft.DataColumn(label=ft.Text("Username")),
            ft.DataColumn(label=ft.Text("Role")),
            ft.DataColumn(label=ft.Text("Date Created")),
            ft.DataColumn(label=ft.Text("Actions")),
        ]

        rows = []
        for user in users:
            edit_button = ft.IconButton(
                icon=ft.Icons.EDIT,
                tooltip="Edit user",
                on_click=lambda e, u=user: self._open_edit_dialog(u)
            )

            if user.role != SALESPERSON_ROLE:
                delete_button = ft.IconButton(
                    icon=ft.Icons.DELETE,
                    tooltip="Delete user",
                    icon_color=ft.Colors.RED_ACCENT_700,
                    on_click=lambda e, u=user: self._confirm_delete_dialog(u)
                )
                actions_cell = ft.DataCell(ft.Row(controls=[edit_button, delete_button], spacing=0))
            else:
                actions_cell = ft.DataCell(ft.Row(controls=[edit_button], spacing=0))

            row = ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(user.username)),
                    ft.DataCell(ft.Text(user.role)),
                    ft.DataCell(ft.Text(user.created_date.strftime("%Y-%m-%d"))),
                    actions_cell,
                ]
            )
            rows.append(row)

        return ft.DataTable(columns=columns, rows=rows)

    def _close_dialog(self, e=None):
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()

    def _open_edit_dialog(self, user: User):
        self.current_edit_user = user

        # Create fields specifically for this dialog instance
        # Username is not editable as it's a unique identifier
        username_field = ft.TextField(label="Username", value=user.username, disabled=True)
        # Role is editable
        role_field = ft.Dropdown(label="Role", value=user.role, autofocus=True)

        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Edit User: {user.username}"),
            content=ft.Column(
                [
                    username_field,
                    role_field,
                ],
                tight=True,
                spacing=15,
            ),
            actions=[
                ft.TextButton("Save", on_click=lambda e: self._save_edits(role_field)),
                ft.TextButton("Cancel", on_click=self._close_dialog),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog.open = True
        self.page.update()

    def _save_edits(self, role_field_control: ft.Dropdown):
        if self.current_edit_user:
            new_role = role_field_control.value
            # Find the user in the self.users list and update their role
            for u_idx, u_obj in enumerate(self.users):
                if u_obj.username == self.current_edit_user.username:
                    # Create a new User instance with the updated role or update the existing one
                    # This depends on whether User objects are mutable or if you prefer immutability.
                    # For simplicity, assuming User objects' attributes can be directly modified:
                    self.users[u_idx].role = new_role
                    # In a real application, you would save this change to the database here.
                    # For example:
                    # with get_db_session() as db:
                    #     update_user_role(db, self.current_edit_user.username, new_role)
                    #     db.commit()
                    break

        self._close_dialog()
        # Re-render the table to reflect changes
        self.content = self._build_layout()
        self.update() # Request Flet to update this component

    def _confirm_delete_dialog(self, user: User):
        self.current_delete_user = user

        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete user '{user.username}'? This action cannot be undone."),
            actions=[
                ft.TextButton("Delete", style=ft.ButtonStyle(color=ft.Colors.RED), on_click=self._handle_delete_confirmed),
                ft.TextButton("Cancel", on_click=self._close_dialog),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.dialog.open = True
        self.page.update()

    def _handle_delete_confirmed(self, e):
        if self.current_delete_user:
            # Remove the user from the self.users list
            self.users = [u for u in self.users if u.username != self.current_delete_user.username]

            # In a real application, you would delete the user from the database here.
            # For example:
            # with get_db_session() as db:
            #     delete_user_by_username(db, self.current_delete_user.username)
            #     db.commit()

        self._close_dialog()
        # Re-render the table
        self.content = self._build_layout()
        self.update()

