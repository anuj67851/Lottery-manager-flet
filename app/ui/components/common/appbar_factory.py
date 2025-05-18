from typing import List, Optional
import flet as ft

from app.constants import LOGIN_ROUTE # Assuming LOGIN_ROUTE is where logout leads

def create_appbar(
        page: ft.Page,
        router: any,
        title_text: str,
        current_user: Optional[any] = None,
        license_status: Optional[bool] = None,
        leading_widget: Optional[ft.Control] = None,
        custom_actions: Optional[List[ft.Control]] = None,
        show_logout_button: bool = True,
        show_user_info: bool = True,
        show_license_status: bool = True,
) -> ft.AppBar:
    """
    Factory function to create a standardized AppBar.
    """
    actions = []

    if show_user_info and current_user and hasattr(current_user, 'username'):
        actions.append(ft.Text(f"User: {current_user.username}", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE))
        actions.append(ft.Container(width=10))

    if show_license_status and license_status is not None:
        actions.append(ft.Text(f"License: {'Active' if license_status else 'Inactive'}", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE))
        actions.append(ft.Container(width=10))

    if custom_actions:
        actions.extend(custom_actions)

    if show_logout_button:
        def logout(e):
            # Potentially clear session data here if needed before navigating
            if hasattr(router, 'current_user'): # If router manages current_user state
                router.current_user = None
            elif hasattr(page, 'client_storage'): # Example: clear from client storage
                page.client_storage.remove("current_user_id") # type: ignore

            router.navigate_to(LOGIN_ROUTE)

        actions.append(
            ft.IconButton(
                icon=ft.Icons.LOGOUT,
                tooltip="Logout",
                icon_color=ft.Colors.WHITE,
                on_click=logout,
            )
        )

    return ft.AppBar(
        leading=leading_widget,
        leading_width=70 if leading_widget else None,
        title=ft.Text(title_text),
        bgcolor=ft.Colors.BLUE_700, # Consistent AppBar color
        color=ft.Colors.WHITE,
        actions=actions if actions else None,
    )