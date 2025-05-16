import flet as ft

class LoginForm(ft.UserControl):
    def __init__(self, on_submit):
        super().__init__()
        self.on_submit = on_submit

    def build(self):
        self.username_field = ft.TextField(label="Username")
        self.password_field = ft.TextField(label="Password", password=True)
        self.error_text = ft.Text("", color="red")

        return ft.Column(
            controls=[
                self.username_field,
                self.password_field,
                self.error_text,
                ft.ElevatedButton("Login", on_click=self.handle_click),
            ],
            width=300,
        )

    def handle_click(self, e):
        username = self.username_field.value
        password = self.password_field.value
        self.on_submit(username, password)

    def show_error(self, message):
        self.error_text.value = message
        self.update()