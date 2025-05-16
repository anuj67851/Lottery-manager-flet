import flet as ft
from app.ui.components.login_form import LoginForm
from app.core.auth_service import authenticate_user

class LoginView(ft.UserControl):
    def __init__(self, page, router, **params):
        super().__init__()
        self.page = page
        self.router = router

    def build(self):
        self.login_form = LoginForm(on_submit=self.handle_login)

        return ft.Column(
            controls=[
                ft.Text("Lottery Manager", size=30, weight=ft.FontWeight.BOLD),
                self.login_form,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def handle_login(self, username, password):
        user = authenticate_user(username, password)
        if user:
            if user.role == "admin":
                self.router.navigate_to("admin_dashboard", user=user)
            else:
                self.router.navigate_to("employee_dashboard", user=user)
        else:
            self.login_form.show_error("Invalid username or password")