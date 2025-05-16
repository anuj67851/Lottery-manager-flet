import flet as ft

class Router:
    def __init__(self, page: ft.Page):
        self.page = page
        self.routes = {
            # "login": LoginView,
        }
        self.current_view = None

    def navigate_to(self, route_name, **params):
        # Clear the page
        self.page.controls.clear()

        # Create the new view
        if route_name in self.routes:
            view_class = self.routes[route_name]
            self.current_view = view_class(self.page, self, **params)
            self.page.add(self.current_view)
            self.page.update()