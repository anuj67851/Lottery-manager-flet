import flet as ft
from sqlalchemy.exc import OperationalError
import logging
import logging.handlers # TimedRotatingFileHandler is here
import sys

from app.ui.router import Router
from app.data.database import init_db, get_db_session
from app.constants import LOGIN_ROUTE, FIRST_RUN_SETUP_ROUTE
from app.config import APP_TITLE, DEFAULT_THEME_MODE, DB_BASE_DIR, VERSION, LOGS_BASE_DIR
from app.services import UserService
from app.core.exceptions import DatabaseError

logger = logging.getLogger("lottery_manager_app")

def setup_logging():
    """Configures logging for the application with daily rotation."""
    logger.setLevel(logging.INFO)

    # Ensure the logs directory exists before creating the log file
    try:
        LOGS_BASE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"ERROR: Could not create logs directory at {LOGS_BASE_DIR.resolve()}. Error: {e}")
        # Fall back to console-only logging
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.DEBUG)
        logger.addHandler(console_handler)
        logger.warning(f"Logging directory creation failed. Using console-only logging.")
        return

    # Base log filename. TimedRotatingFileHandler will append date to rotated files.
    base_log_filename = f"{APP_TITLE.lower().replace(' ', '_')}.log"
    log_file_path = LOGS_BASE_DIR.joinpath(base_log_filename)

    # --- TimedRotatingFileHandler for daily rotation ---
    try:
        timed_file_handler = logging.handlers.TimedRotatingFileHandler(
            log_file_path,
            when='midnight',
            interval=1,
            backupCount=15, # Keep logs for 15 days, adjust as needed
            encoding='utf-8',
            delay=False, # Set to False as we ensure directory exists
            utc=False
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
        )
        timed_file_handler.setFormatter(file_formatter)
        logger.addHandler(timed_file_handler)
    except Exception as e:
        print(f"ERROR: Could not create log file handler. Error: {e}")
        # Continue with console-only logging

    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.DEBUG) # Or INFO for less console verbosity
    logger.addHandler(console_handler)

    logger.info(f"--- Logging initialized for {APP_TITLE} v{VERSION} ---")
    if log_file_path.exists() or log_file_path.parent.exists():
        logger.info(f"Log file: {log_file_path.resolve()} (rotates daily, keeps 15 backups)")
    else:
        logger.warning("File logging unavailable - using console logging only")

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

    # Prepare the log file name for UI messages *before* any potential error that prevents setup_logging
    # This is a bit redundant now since setup_logging defines it, but safe for UI error messages.
    ui_log_filename = f"{APP_TITLE.lower().replace(' ', '_')}.log"

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
            ft.Text(f"Please check logs at '{DB_BASE_DIR.joinpath(ui_log_filename)}' for details.", text_align=ft.TextAlign.CENTER, size=12),
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
            ft.Text(f"Please check logs at '{DB_BASE_DIR.joinpath(ui_log_filename)}' for details.", text_align=ft.TextAlign.CENTER, size=12),
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