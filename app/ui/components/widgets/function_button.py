from typing import Any, Optional, Dict, Callable # Added Callable
import flet as ft

def create_nav_card_button(
        router: Any,  # Can be your app's Router instance or page for page.go
        text: str,
        icon_name: str, # e.g., ft.icons.HOME_ROUNDED
        accent_color: str, # e.g., ft.colors.BLUE_ACCENT_700
        navigate_to_route: Optional[str] = None, # Made optional
        on_click_override: Optional[Callable[[ft.ControlEvent], None]] = None, # New parameter
        router_params: Optional[Dict[str, Any]] = None,
        icon_size: int = 40,
        border_radius: int = 12,
        background_opacity: float = 0.15,
        shadow_opacity: float = 0.25,
        disabled: bool = False,
        tooltip: Optional[str] = None,
        height: float = 150,
        width: float = 150,
) -> ft.Card:

    effective_router_params = router_params if router_params is not None else {}

    def handle_click(e: ft.ControlEvent):
        if disabled:
            return

        if on_click_override:
            on_click_override(e)
        elif navigate_to_route:
            # print(f"NavCard Clicked: Navigating to {navigate_to_route} with params {effective_router_params}")
            if hasattr(router, 'navigate_to'):
                router.navigate_to(navigate_to_route, **effective_router_params)
            elif hasattr(router, 'go'): # For Flet's page.go
                router.go(navigate_to_route)
            else:
                print("Router object not recognized or navigation method missing.")
        else:
            print(f"NavCard '{text}' clicked, but no navigation route or override handler defined.")


    button_internal_content = ft.Column(
        [
            ft.Icon(
                name=icon_name,
                size=icon_size,
                color=ft.Colors.with_opacity(0.9, accent_color) if not disabled else ft.Colors.ON_SURFACE_VARIANT,
            ),
            ft.Container(height=5),
            ft.Text(
                text,
                weight=ft.FontWeight.W_500,
                size=14,
                text_align=ft.TextAlign.CENTER,
                color=ft.Colors.with_opacity(0.85, accent_color) if not disabled else ft.Colors.ON_SURFACE_VARIANT,
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=4,
    )

    clickable_area = ft.Container(
        content=button_internal_content,
        alignment=ft.alignment.center,
        padding=15,
        border_radius=ft.border_radius.all(border_radius),
        ink=not disabled,
        on_click=handle_click if not disabled else None,
        bgcolor=ft.Colors.with_opacity(background_opacity, accent_color) if not disabled else ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE),
        tooltip=tooltip if not disabled else "Disabled",
        height=height,
        width=width,
    )

    return ft.Card(
        content=clickable_area,
        elevation=5 if not disabled else 1,
        shadow_color=ft.Colors.with_opacity(shadow_opacity, accent_color) if not disabled else ft.Colors.BLACK26,
    )