import flet as ft

from app.ui.views.admin import SalesEntryView
from app.ui.views.admin.reports import BookOpenReportView, GameExpiryReportView, StockLevelsReportView
from app.ui.views.admin.reports.sales_by_date_report_view import SalesByDateReportView
from app.ui.views.admin.user_management import AdminUserManagementView
from app.ui.views.login_view import LoginView
from app.ui.views.admin_dashboard_view import AdminDashboardView
from app.ui.views.employee_dashboard_view import EmployeeDashboardView
from app.ui.views.salesperson_dashboard_view import SalesPersonDashboardView
from app.ui.views.admin.game_management import GameManagementView
from app.ui.views.admin.book_management import BookManagementView
from app.ui.views.first_run_setup_view import FirstRunSetupView # Import the new view

import logging
logger = logging.getLogger(__name__)

# Import constants for route names
from app.constants import (
    FIRST_RUN_SETUP_ROUTE, # Added
    LOGIN_ROUTE, ADMIN_DASHBOARD_ROUTE, EMPLOYEE_DASHBOARD_ROUTE,
    SALESPERSON_DASHBOARD_ROUTE, GAME_MANAGEMENT_ROUTE, BOOK_MANAGEMENT_ROUTE, SALES_ENTRY_ROUTE,
    ADMIN_USER_MANAGEMENT_ROUTE, SALES_BY_DATE_REPORT_ROUTE, STOCK_LEVELS_REPORT_ROUTE, GAME_EXPIRY_REPORT_ROUTE,
    BOOK_OPEN_REPORT_ROUTE
)

class Router:
    def __init__(self, page: ft.Page):
        self.page = page
        self.routes = {
            FIRST_RUN_SETUP_ROUTE: FirstRunSetupView, # Added
            LOGIN_ROUTE: LoginView,
            ADMIN_DASHBOARD_ROUTE: AdminDashboardView,
            EMPLOYEE_DASHBOARD_ROUTE: EmployeeDashboardView,
            SALESPERSON_DASHBOARD_ROUTE: SalesPersonDashboardView,
            GAME_MANAGEMENT_ROUTE: GameManagementView,
            BOOK_MANAGEMENT_ROUTE: BookManagementView,
            SALES_ENTRY_ROUTE: SalesEntryView,
            ADMIN_USER_MANAGEMENT_ROUTE: AdminUserManagementView,
            SALES_BY_DATE_REPORT_ROUTE: SalesByDateReportView,
            BOOK_OPEN_REPORT_ROUTE: BookOpenReportView,
            GAME_EXPIRY_REPORT_ROUTE: GameExpiryReportView,
            STOCK_LEVELS_REPORT_ROUTE: StockLevelsReportView,
        }
        self.current_view_instance = None # Keep track of the current view instance
        self.current_route_name = None    # Keep track of current route name

    def navigate_to(self, route_name: str, **params):
        """
        Navigates to the specified route, clearing the page and instantiating the new view.
        """
        # Clear previous view's specific elements if they exist and route is changing
        if self.current_route_name != route_name:
            self.page.controls.clear()
            self.page.appbar = None # Views are responsible for their own AppBars
            self.page.dialog = None # Clear any existing dialog
            self.page.banner = None # Clear any existing banner
            self.page.snack_bar = None # Clear any existing snackbar
            # self.current_view_instance = None # Reset instance reference

        self.current_route_name = route_name

        if route_name in self.routes:
            view_class = self.routes[route_name]
            try:
                # Instantiate the view, passing the page, router, and any other params
                self.current_view_instance = view_class(page=self.page, router=self, **params)
                self.page.add(self.current_view_instance)
            except Exception as e:
                logger.error(f"Error instantiating view for route '{route_name}': {e}", exc_info=True)
                # Fallback or error display logic
                self.page.controls.clear() # Clear potentially broken UI
                self.page.add(ft.Text(f"Error loading page: {route_name}. Details: {e}", color=ft.Colors.RED))
                # Optionally navigate to a known safe route like login
                # Avoid infinite loop if FIRST_RUN_SETUP_ROUTE itself fails
                if route_name != LOGIN_ROUTE and route_name != FIRST_RUN_SETUP_ROUTE:
                    self.navigate_to(LOGIN_ROUTE)
        else:
            logger.error(f"Error: Route '{route_name}' not found. Navigating to login as fallback.", exc_info=True)
            self.page.controls.clear()
            # Fallback to login view if route is unknown (should ideally not happen if initial check is correct)
            login_view_class = self.routes[LOGIN_ROUTE]
            self.current_view_instance = login_view_class(page=self.page, router=self) # No params for login usually
            self.page.add(self.current_view_instance)
            self.current_route_name = LOGIN_ROUTE

        self.page.update()