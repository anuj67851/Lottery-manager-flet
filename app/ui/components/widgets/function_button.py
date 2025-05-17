from typing import Any, Optional, Dict

import flet as ft

def create_nav_card_button(
        router: Any,  # Can be your app's Router instance or page for page.go
        text: str,
        icon_name: str, # e.g., ft.icons.HOME_ROUNDED
        accent_color: str, # e.g., ft.colors.BLUE_ACCENT_700
        navigate_to_route: str,
        router_params: Optional[Dict[str, Any]] = None,
        icon_size: int = 40,
        border_radius: int = 12,
        background_opacity: float = 0.15, # Opacity for the card's background tint
        shadow_opacity: float = 0.25,    # Opacity for the shadow color tint
        disabled: bool = False,
        tooltip: Optional[str] = None,
        height: float = 150,
        width: float = 150,
) -> ft.Card:

    effective_router_params = router_params if router_params is not None else {}

    def handle_click(e):
        if disabled:
            return
        print(f"NavCard Clicked: Navigating to {navigate_to_route} with params {effective_router_params}")
        if hasattr(router, 'navigate_to'): # For your custom Router class
            router.navigate_to(navigate_to_route, **effective_router_params)
        else:
            print("Router object not recognized or navigation method missing.")

    # Content of the button (icon and text)
    button_internal_content = ft.Column(
        [
            ft.Icon(
                name=icon_name,
                size=icon_size,
                color=ft.Colors.with_opacity(0.9, accent_color) if not disabled else ft.Colors.ON_SURFACE_VARIANT,
            ),
            ft.Container(height=5), # Small spacer
            ft.Text(
                text,
                weight=ft.FontWeight.W_500,
                size=14, # Slightly smaller default text
                text_align=ft.TextAlign.CENTER,
                color=ft.Colors.with_opacity(0.85, accent_color) if not disabled else ft.Colors.ON_SURFACE_VARIANT, # Text also tinted
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=4, # Reduced spacing between icon and text
    )

    clickable_area = ft.Container(
        content=button_internal_content,
        alignment=ft.alignment.center,
        padding=15, # Padding inside the clickable area
        border_radius=border_radius,
        ink=not disabled, # Ripple effect on click
        on_click=handle_click if not disabled else None,
        bgcolor=ft.Colors.with_opacity(background_opacity, accent_color) if not disabled else ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE),
        tooltip=tooltip if not disabled else "Disabled",
        height=height,
        width=width,
    )

    return ft.Card(
        content=clickable_area,
        elevation=5 if not disabled else 1, # Control shadow depth
        shadow_color=ft.Colors.with_opacity(shadow_opacity, accent_color) if not disabled else ft.Colors.BLACK26,
    )