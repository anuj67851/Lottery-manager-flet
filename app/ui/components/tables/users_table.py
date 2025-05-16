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
        ]

        rows = []
        for user in users:
            row = ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(user.username)),
                    ft.DataCell(ft.Text(user.role)),
                    ft.DataCell(ft.Text(user.created_date.strftime("%Y-%m-%d"))),
                ]
            )
            rows.append(row)

        # Create the DataTable
        return ft.DataTable(columns=columns, rows=rows)
