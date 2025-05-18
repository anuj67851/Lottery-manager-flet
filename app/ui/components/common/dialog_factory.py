from typing import Callable, Optional
import flet as ft

def create_confirmation_dialog(
        title_text: str,
        content_control: ft.Control, # Changed from content_text to allow richer content
        on_confirm: Callable,
        on_cancel: Callable, # Added explicit on_cancel
        confirm_button_text: str = "Confirm",
        cancel_button_text: str = "Cancel",
        confirm_button_style: Optional[ft.ButtonStyle] = None,
        modal: bool = True,
        title_color: Optional[str] = None,
) -> ft.AlertDialog:
    """
    Creates a standardized confirmation dialog.
    The caller is responsible for assigning this to page.dialog and opening it.
    """
    default_confirm_style = ft.ButtonStyle(bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE)
    if confirm_button_style and confirm_button_style.bgcolor: # type: ignore
        pass # use provided style
    else: # use default if no specific bgcolor provided, to keep critical confirmations distinct
        confirm_button_style = default_confirm_style


    return ft.AlertDialog(
        modal=modal,
        title=ft.Text(title_text, color=title_color),
        content=content_control,
        actions=[
            ft.TextButton(cancel_button_text, on_click=on_cancel),
            ft.FilledButton(
                confirm_button_text,
                on_click=on_confirm,
                style=confirm_button_style
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

def create_form_dialog(
        page: ft.Page, # page might be needed for width calculations
        title_text: str,
        form_content_column: ft.Column, # Expects a Column with fields and an error_text
        on_save_callback: Callable, # Callback to execute on save
        on_cancel_callback: Callable,
        save_button_text: str = "Save",
        cancel_button_text: str = "Cancel",
        width_ratio: float = 0.35, # Ratio of page width
        min_width: int = 400
) -> ft.AlertDialog:
    """
    Creates a dialog for forms.
    The form_content_column should ideally contain form fields and a ft.Text for errors.
    The on_save_callback will be called when the save button is clicked; it should handle
    form validation and the actual saving logic.
    """
    dialog_width = max(min_width, page.width * width_ratio if page.width else min_width)

    return ft.AlertDialog(
        modal=True,
        title=ft.Text(title_text),
        content=ft.Container(
            content=form_content_column, # The column with all form elements
            padding=ft.padding.symmetric(horizontal=24, vertical=20),
            border_radius=8,
            width=dialog_width,
        ),
        actions=[
            ft.TextButton(cancel_button_text, on_click=on_cancel_callback, style=ft.ButtonStyle(color=ft.Colors.BLUE_GREY)),
            ft.FilledButton(save_button_text, on_click=on_save_callback),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )