import flet as ft
from app.data.database import init_db
from app.ui.router import Router

def main(page: ft.Page):
    # Configure page
    page.title = "Lottery Manager"
    page.theme_mode = ft.ThemeMode.LIGHT

    # Initialize database
    init_db()

    # Set up router
    router = Router(page)

    # Start with login view
    router.navigate_to("login")

    # Update the page
    page.update()


if __name__ == "__main__":
    # Run the app
    ft.app(target=main)