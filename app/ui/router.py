import flet as ft

from app.ui.views.login_view import LoginView
from app.ui.views.admin_dashboard_view import AdminDashboardView
from app.ui.views.employee_dashboard_view import EmployeeDashboardView
# Import constants
from app.constants import LOGIN_ROUTE, ADMIN_DASHBOARD_ROUTE, EMPLOYEE_DASHBOARD_ROUTE, SALESPERSON_DASHBOARD_ROUTE
from app.ui.views.salesperson_dashboard_view import SalesPersonDashboardView


class Router:
    def __init__(self, page: ft.Page):
        self.page = page
        self.routes = {
            LOGIN_ROUTE: LoginView,
            ADMIN_DASHBOARD_ROUTE: AdminDashboardView,
            EMPLOYEE_DASHBOARD_ROUTE: EmployeeDashboardView,
            SALESPERSON_DASHBOARD_ROUTE: SalesPersonDashboardView,
        }
        self.current_view = None # Keep track of the current view instance

    def navigate_to(self, route_name, **params):
        # Clear the page only if a new view is being loaded
        if self.current_view:
            self.page.controls.clear() # Or self.page.remove(self.current_view) if only one view is added

        if route_name in self.routes:
            view_class = self.routes[route_name]
            # Instantiate the view, applying the white screen fix pattern
            self.current_view = view_class(page=self.page, router=self, **params)
            self.page.add(self.current_view)
        else:
            # Handle unknown route, e.g., show a "Not Found" view or navigate to login
            print(f"Error: Route '{route_name}' not found. Navigating to login.")
            self.current_view = self.routes[LOGIN_ROUTE](page=self.page, router=self)
            self.page.add(self.current_view)

        self.page.update()