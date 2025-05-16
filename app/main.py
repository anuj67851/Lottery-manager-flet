import flet as ft
from app.ui.router import Router
from app.data.database import init_db
from app.constants import LOGIN_ROUTE # Use constant
from app.config import APP_TITLE, DEFAULT_THEME_MODE # Use config

def main(page: ft.Page):
    # Configure page
    page.title = APP_TITLE
    if DEFAULT_THEME_MODE.lower() == "dark":
        page.theme_mode = ft.ThemeMode.DARK
    else:
        page.theme_mode = ft.ThemeMode.LIGHT

    # Initialize database
    init_db()

    # Set up router
    router = Router(page)

    # Start with login view
    router.navigate_to(LOGIN_ROUTE) # Use constant

    # Update the page
    page.update()


if __name__ == "__main__":
    # Run the app
    ft.app(target=main)