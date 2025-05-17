import flet as ft

from app.ui.views.admin.game_management import GameManagementView
from app.ui.views.login_view import LoginView
from app.ui.views.admin_dashboard_view import AdminDashboardView
from app.ui.views.employee_dashboard_view import EmployeeDashboardView
# Import constants
from app.constants import LOGIN_ROUTE, ADMIN_DASHBOARD_ROUTE, EMPLOYEE_DASHBOARD_ROUTE, SALESPERSON_DASHBOARD_ROUTE, \
    GAME_MANAGEMENT_ROUTE
from app.ui.views.salesperson_dashboard_view import SalesPersonDashboardView


class Router:
    def __init__(self, page: ft.Page):
        self.page = page
        self.routes = {
            LOGIN_ROUTE: LoginView,
            ADMIN_DASHBOARD_ROUTE: AdminDashboardView,
            EMPLOYEE_DASHBOARD_ROUTE: EmployeeDashboardView,
            SALESPERSON_DASHBOARD_ROUTE: SalesPersonDashboardView,
            GAME_MANAGEMENT_ROUTE: GameManagementView,
        }
        self.current_view = None # Keep track of the current view instance
        self.current_route_name = None # Keep track of current route name

    def navigate_to(self, route_name, **params):
        # Clear the page only if a new view is being loaded or route changes
        if self.current_view and self.current_route_name != route_name:
            self.page.controls.clear() # Clear all controls
            self.page.appbar = None    # Clear appbar too if views manage it
            self.page.dialog = None    # Clear any open dialogs
            self.current_view = None   # Reset current view

        self.current_route_name = route_name # Update current route name

        if route_name in self.routes:
            view_class = self.routes[route_name]
            # Instantiate the view, applying the white screen fix pattern
            self.current_view = view_class(page=self.page, router=self, **params)
            self.page.add(self.current_view)
        else:
            # Handle unknown route, e.g., show a "Not Found" view or navigate to login
            print(f"Error: Route '{route_name}' not found. Navigating to login.")
            # Fallback to login view
            login_view_class = self.routes[LOGIN_ROUTE]
            self.current_view = login_view_class(page=self.page, router=self)
            self.page.add(self.current_view)
            self.current_route_name = LOGIN_ROUTE

        self.page.update()
