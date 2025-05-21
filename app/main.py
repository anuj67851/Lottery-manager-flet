import flet as ft
from sqlalchemy.exc import OperationalError
import logging
import logging.handlers
import sys

from app.ui.router import Router
from app.data.database import init_db, get_db_session
from app.constants import LOGIN_ROUTE, FIRST_RUN_SETUP_ROUTE
from app.config import APP_TITLE, DEFAULT_THEME_MODE, DB_BASE_DIR, VERSION
from app.services import UserService
from app.core.exceptions import DatabaseError

logger = logging.getLogger("lottery_manager_app")

def setup_logging():
    """Configures logging for the application."""
    logger.setLevel(logging.INFO)

    log_file_name = f"{APP_TITLE.lower().replace(' ', '_')}_{VERSION}.log"
    log_file_path = DB_BASE_DIR.joinpath(log_file_name)

    file_handler = logging.handlers.RotatingFileHandler(
        log_file_path, maxBytes=1*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)

    logger.info(f"--- Logging initialized for {APP_TITLE} v{VERSION} ---")
    logger.info(f"Log file location: {log_file_path.resolve()}")

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical("Unhandled exception:", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception


def main(page: ft.Page):
    try:
        DB_BASE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        initial_error_message = f"CRITICAL ERROR: Could not create data directory at {DB_BASE_DIR.resolve()}. Error: {e}. Logging might be affected."
        print(initial_error_message)
        page.add(ft.Column([
            ft.Text(APP_TITLE, size=24, weight=ft.FontWeight.BOLD),
            ft.Text(initial_error_message, color=ft.Colors.RED, size=16)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, expand=True))
        page.update()
        return

    try:
        setup_logging()
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to initialize logging system: {e}")

    logger.info("Application starting...")

    page.title = APP_TITLE
    page.window.maximized = True
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE_GREY, use_material3=True)
    page.theme_mode = ft.ThemeMode.DARK if DEFAULT_THEME_MODE.lower() == "dark" else ft.ThemeMode.LIGHT
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    router = None
    initial_route = LOGIN_ROUTE
    log_file_name_for_ui = f"{APP_TITLE.lower().replace(' ', '_')}_{VERSION}.log" # Prepare for UI message

    try:
        init_db()
        router = Router(page)
        user_service = UserService()
        with get_db_session() as db:
            if not user_service.any_users_exist(db):
                initial_route = FIRST_RUN_SETUP_ROUTE
                logger.info(f"No users found. Navigating to First Run Setup: {initial_route}")
            else:
                logger.info(f"Users exist. Navigating to Login: {initial_route}")

    except (DatabaseError, OperationalError) as e:
        error_message = "A critical database error occurred during application startup."
        logger.critical(error_message, exc_info=True)
        page.controls.clear(); page.appbar = None
        page.add(ft.Column([
            ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, color=ft.Colors.RED_ACCENT_700, size=60),
            ft.Text(APP_TITLE, size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
            ft.Text("Application Startup Failed: Database Error", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_700, text_align=ft.TextAlign.CENTER),
            ft.Container(height=10),
            ft.Text(f"Please check logs at '{DB_BASE_DIR.joinpath(log_file_name_for_ui)}' for details.", text_align=ft.TextAlign.CENTER, size=12), # Corrected line
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, spacing=10, expand=True))
        page.update()
        return
    except Exception as e:
        error_message = "An unexpected critical error occurred during application startup."
        logger.critical(error_message, exc_info=True)
        page.controls.clear(); page.appbar = None
        page.add(ft.Column([
            ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, color=ft.Colors.RED_ACCENT_700, size=60),
            ft.Text(APP_TITLE, size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
            ft.Text("Application Startup Failed: Unexpected Error", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_700, text_align=ft.TextAlign.CENTER),
            ft.Container(height=10),
            ft.Text(f"Please check logs at '{DB_BASE_DIR.joinpath(log_file_name_for_ui)}' for details.", text_align=ft.TextAlign.CENTER, size=12), # Corrected line
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, spacing=10, expand=True))
        page.update()
        return

    if router:
        logger.info(f"Navigating to initial route: {initial_route}")
        router.navigate_to(initial_route)
    else:
        logger.error("Router not initialized due to startup error. Cannot navigate.")
        if not page.controls:
            page.add(ft.Text("Failed to initialize router. Application cannot start.", color=ft.Colors.RED, size=16))
        page.update()

    logger.info("Application main function completed setup.")

if __name__ == "__main__":
    ft.app(target=main)