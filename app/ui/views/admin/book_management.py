import flet as ft

from app.constants import LOGIN_ROUTE, ADMIN_DASHBOARD_ROUTE
from app.core.models import User # Import User model for type hinting
from app.ui.components.common.appbar_factory import create_appbar # Import AppBar factory


class BookManagementView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user: User, license_status: bool,
                 previous_view_route: str = ADMIN_DASHBOARD_ROUTE, # Default previous route
                 previous_view_params: dict = None, # Params to reconstruct previous view
                 **params):
        super().__init__(expand=True)
        self.page = page
        self.router = router
        self.current_user = current_user
        self.license_status = license_status

        self.previous_view_route = previous_view_route
        # Ensure previous_view_params is a dict, even if None is passed
        self.previous_view_params = previous_view_params if previous_view_params is not None else {}

        self.page.appbar = create_appbar(
            page=self.page,
            router=self.router,
            title_text="Admin > Book Management", # More specific title
            current_user=self.current_user,
            license_status=self.license_status,
            leading_widget=ft.IconButton( # Back button
                icon=ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                tooltip="Go Back",
                icon_color=ft.Colors.WHITE,
                on_click=self._go_back,
            )
        )
        self.content = self._build_body()

    def _go_back(self, e):
        """Handles the click event for the back button, navigating to the stored previous view."""
        # Pass current_user and license_status if they are part of previous_view_params structure
        # The ADMIN_DASHBOARD_ROUTE expects current_user and license_status
        nav_params = {**self.previous_view_params} # Start with stored params
        if "current_user" not in nav_params and self.current_user: # Ensure current_user is passed back if needed
            nav_params["current_user"] = self.current_user
        if "license_status" not in nav_params and self.license_status is not None:
            nav_params["license_status"] = self.license_status

        self.router.navigate_to(self.previous_view_route, **nav_params)


    def _build_body(self) -> ft.Column: # Return type hint
        # Placeholder content for Book Management
        # This area would typically include a table for books, add/edit buttons, search, etc.
        # For example, a PaginatedDataTable for books.

        # Example: Add New Book Button (placeholder action)
        add_book_button = ft.FilledButton(
            "Add New Book",
            icon=ft.Icons.ADD_CIRCLE_OUTLINE_ROUNDED,
            on_click=lambda e: self.page.open(ft.SnackBar(ft.Text("Add New Book - Not Implemented"), open=True)),
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
        )

        # Example: Search field (placeholder)
        search_field = ft.TextField(
            label="Search Books (e.g., Book Number, Game Name)",
            hint_text="Type to search books...",
            prefix_icon=ft.Icons.SEARCH,
            border_radius=8,
            expand=True,
            # on_change=self._on_book_search_change, # Would need a handler
        )

        # Placeholder for a table or list of books
        books_display_area = ft.Container(
            content=ft.Text("Book listing area (e.g., a table of books will be here).", italic=True),
            padding=20,
            border=ft.border.all(1, ft.Colors.OUTLINE), # type: ignore
            border_radius=ft.border_radius.all(8),
            expand=True,
        )


        return ft.Column(
            controls=[
                ft.Text("Book Management", style=ft.TextThemeStyle.HEADLINE_MEDIUM, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Row([search_field, add_book_button], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                books_display_area,
                # Additional controls for book management...
            ],
            alignment=ft.MainAxisAlignment.START, # Align content to the top
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH, # Stretch children like search row
            spacing=20, # Spacing between elements
            expand=True,
        )
