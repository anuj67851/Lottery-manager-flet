import flet as ft

from app.constants import LOGIN_ROUTE, ADMIN_DASHBOARD_ROUTE # Assuming ADMIN_DASHBOARD_ROUTE is where you go back to


class GameManagementView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user, license_status,
                 previous_view_route: str = ADMIN_DASHBOARD_ROUTE,
                 previous_view_params: dict = None,
                 **params):
        super().__init__(expand=True)
        self.page = page
        self.router = router
        self.current_user = current_user
        self.license_status = license_status

        # Store the route and params for the "Go Back" functionality
        self.previous_view_route = previous_view_route
        self.previous_view_params = previous_view_params if previous_view_params is not None else {}

        self.page.appbar = self._build_appbar()
        self.content = self._build_body()

    def logout(self, e):
        self.current_user = None
        self.router.navigate_to(LOGIN_ROUTE)

    def _go_back(self, e):
        """Handles the click event for the back button."""
        self.router.navigate_to(self.previous_view_route, **self.previous_view_params)


    def _build_appbar(self):
        return ft.AppBar(
            # Adding the back button as the leading action
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED, # A common back icon
                tooltip="Go Back",
                icon_color=ft.Colors.WHITE,
                on_click=self._go_back,
            ),
            leading_width=70, # Give some space for the back button
            title=ft.Text("Admin Dashboard > Game Management"),
            bgcolor=ft.Colors.BLUE_700,
            color=ft.Colors.WHITE,
            actions=[
                ft.Text(f"Current User: {self.current_user.username}", weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE),
                ft.Container(width=20),
                ft.Text(f"License: {'Active' if self.license_status else 'Inactive'}", weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE),
                ft.Container(width=20),
                ft.IconButton(
                    icon=ft.Icons.LOGOUT,
                    tooltip="Logout",
                    icon_color=ft.Colors.WHITE,
                    on_click=self.logout,
                ),
            ],
        )

    def _build_body(self):
        # Placeholder for Game Management content
        # Replace this with your actual game management UI (e.g., a table of games, add/edit forms)
        return ft.Column(
            controls=[
                ft.Text("Game Management Interface", size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Text("Here you will be able to add, edit, and manage game types.", size=16, text_align=ft.TextAlign.CENTER),
                # Example: Add a button to add a new game
                # ft.ElevatedButton(
                #     "Add New Game",
                #     icon=ft.Icons.ADD_ROUNDED,
                #     on_click=lambda e: print("Add New Game Clicked") # Placeholder action
                # ),
                # Example: Placeholder for a DataTable of games
                # ft.DataTable(...)
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            expand=True
        )