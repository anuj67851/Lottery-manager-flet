# Filename: app/ui/components/common/search_bar_component.py
import threading
from typing import Callable, Optional
import flet as ft

class SearchBarComponent(ft.Container):
    def __init__(
            self,
            on_search_changed: Callable[[str], None],
            label: str = "Search...",
            hint_text: str = "Type to search...",
            debounce_time_ms: int = 500, # milliseconds
            expand: bool = True,
            **kwargs
    ):
        super().__init__(expand=expand, **kwargs)
        self.on_search_changed = on_search_changed
        self.debounce_time_seconds = debounce_time_ms / 1000.0
        self._debounce_timer: Optional[threading.Timer] = None

        self.search_field = ft.TextField(
            label=label,
            hint_text=hint_text,
            on_change=self._handle_on_change,
            prefix_icon=ft.Icons.SEARCH,
            border_radius=8,
            expand=True, # TextField expands within its row/container
        )
        self.content = self.search_field # Directly use the TextField as content

    def _handle_on_change(self, e: ft.ControlEvent):
        if self._debounce_timer:
            self._debounce_timer.cancel()

        search_term = e.control.value

        def debounced_action():
            self.on_search_changed(search_term)

        self._debounce_timer = threading.Timer(self.debounce_time_seconds, debounced_action)
        self._debounce_timer.start()

    def get_value(self) -> str:
        return self.search_field.value

    def set_value(self, value: str):
        self.search_field.value = value
        # No need to trigger on_change here, usually set externally for initial state

    # Optional: if the component itself needs to be updated on the page
    # def update(self):
    #     super().update()
    #     self.search_field.update()