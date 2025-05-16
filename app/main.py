import flet as ft
from app.ui.router import Router
from app.data.database import init_db
from app.constants import LOGIN_ROUTE
from app.config import APP_TITLE, DEFAULT_THEME_MODE

def main(page: ft.Page):
    # Configure page
    page.title = APP_TITLE

    page.window.maximized = True

    # Define a Material 3 theme
    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.BLUE_GREY, # You can change this seed color (e.g., INDIGO, TEAL)
        use_material3=True,
    )

    if DEFAULT_THEME_MODE.lower() == "dark":
        page.theme_mode = ft.ThemeMode.DARK
    else:
        page.theme_mode = ft.ThemeMode.LIGHT

    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    init_db()
    router = Router(page)
    router.navigate_to(LOGIN_ROUTE)
    page.update()

if __name__ == "__main__":
    ft.app(target=main)