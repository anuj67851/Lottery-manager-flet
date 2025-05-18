Okay, I've analyzed your Flet project code thoroughly. The goal is to hyper-modularize it, creating reusable components for common UI patterns like AppBars, tables with pagination and sorting, search functionality, and dialogs, while strictly adhering to the existing core functionality and your specific constraints (Snackbar.open(), Icon/Color naming).

Here's a breakdown of the refactoring strategy and the subsequent code changes:

**1. New Directory for Common Reusable Components:**

I'll create a new directory `app/ui/components/common/` to house the generic UI components.

*   `app/ui/components/common/__init__.py`
*   `app/ui/components/common/appbar_factory.py`: For creating standardized AppBars.
*   `app/ui/components/common/dialog_factory.py`: For generating common dialog types (e.g., confirmation).
*   `app/ui/components/common/search_bar_component.py`: A reusable search input with debouncing.
*   `app/ui/components/common/paginated_data_table.py`: A base class for tables requiring pagination and sorting.

**2. Refactoring Plan:**

*   **AppBarFactory:**
    *   A function `create_appbar` will be created. It will build `ft.AppBar` instances with common elements like a title, logout button, user information, license status, and allow for custom leading widgets (like a back button) and additional actions.
    *   Views (`AdminDashboardView`, `EmployeeDashboardView`, `LoginView`, `SalesPersonDashboardView`, `BookManagementView`, `GameManagementView`) will be updated to use this factory for their AppBars.

*   **DialogFactory:**
    *   Functions like `create_confirmation_dialog` will be implemented. This factory will return the dialog instance, and the calling code will be responsible for assigning it to `page.dialog` and opening it, as per your existing pattern (`page.dialog = ...; page.open(page.dialog)`).
    *   Simple confirmation dialogs in `GamesTable` and `UsersTable` will be refactored to use this. More complex form dialogs (like "Add User" or "Edit User") will retain their specific construction logic for now, but the `AlertDialog` shell could potentially use a generic creator from this factory in a future step if desired.

*   **SearchBarComponent:**
    *   This component will encapsulate an `ft.TextField` with built-in debouncing logic for search operations.
    *   The search functionality in `GameManagementView` will be replaced by this component.

*   **PaginatedDataTable:**
    *   This will be a base class inheriting from `ft.Container`. It will manage:
        *   The core `ft.DataTable` instance.
        *   Pagination controls (`prev_button`, `next_button`, `page_info_text`) and their logic.
        *   Sorting state and handling.
        *   A generic `refresh_data` mechanism.
    *   `GamesTable` will be refactored to inherit from `PaginatedDataTable`, implementing abstract methods for column definitions, data fetching, row creation, and sorting logic specific to `Game` objects.
    *   `UsersTable`:
        *   This table currently doesn't have pagination or client-side sorting defined via `on_sort` on `DataColumn` headers.
        *   To make it a "reusable component that works with different types of data" as requested, it will also be refactored to inherit from `PaginatedDataTable`.
        *   Pagination and sorting features will be made optional or minimally intrusive if not actively used, preserving its current primary display function but allowing future enhancements easily. The key is to make the base `PaginatedDataTable` flexible.

*   **Existing Components and Views:**
    *   `app/ui/components/widgets/function_button.py` (for `create_nav_card_button`) and `app/ui/components/widgets/number_decimal_input.py` are already good reusable components and will be retained as is.
    *   Specific view layouts (like the quadrants in `AdminDashboardView`) will be maintained. The focus is on modularizing the *elements* within those layouts.

**3. Adherence to Constraints:**

*   **Core Functionality:** All existing features and business logic will remain unchanged. The refactoring targets UI structure and reusability.
*   **Snackbar.open():** This specific usage for Snackbars will be untouched. Dialogs will continue to use the `page.dialog = ...; page.open(page.dialog)` pattern.
*   **Icon and Color Naming:** `ft.Icons` and `ft.Colors` will be used as they are in your current code (e.g., `ft.Icons.LOGOUT`, not `ft.icons.LOGOUT`).
*   **Layout and Functionality:** While aiming for hyper-modularity, the overall look and feel will be preserved. "Going wild with layout" will be interpreted as creating a cleaner, more maintainable structure rather than drastic visual changes.

This is a significant refactoring. I will proceed by first defining the new common components and then integrating them into your existing files.

```python
# Filename: app/ui/components/common/__init__.py
# This file can remain empty or be used for selective imports
# if you want to simplify access to the common components, e.g.:
# from .appbar_factory import create_appbar
# from .dialog_factory import create_confirmation_dialog
# from .search_bar import SearchBarComponent
# from .paginated_data_table import PaginatedDataTable
```

```python
# Filename: app/ui/components/common/appbar_factory.py
from typing import Callable, List, Optional
import flet as ft

from app.constants import LOGIN_ROUTE # Assuming LOGIN_ROUTE is where logout leads

def create_appbar(
    page: ft.Page,
    router: any, # Your app's Router instance
    title_text: str,
    current_user: Optional[any] = None, # Assuming a User-like object with a 'username' attribute
    license_status: Optional[bool] = None,
    leading_widget: Optional[ft.Control] = None,
    custom_actions: Optional[List[ft.Control]] = None,
    show_logout_button: bool = True,
    show_user_info: bool = True,
    show_license_status: bool = True,
) -> ft.AppBar:
    """
    Factory function to create a standardized AppBar.
    """
    actions = []

    if show_user_info and current_user and hasattr(current_user, 'username'):
        actions.append(ft.Text(f"User: {current_user.username}", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE))
        actions.append(ft.Container(width=10))

    if show_license_status and license_status is not None:
        actions.append(ft.Text(f"License: {'Active' if license_status else 'Inactive'}", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE))
        actions.append(ft.Container(width=10))

    if custom_actions:
        actions.extend(custom_actions)

    if show_logout_button:
        def logout(e):
            # Potentially clear session data here if needed before navigating
            if hasattr(router, 'current_user'): # If router manages current_user state
                router.current_user = None
            elif hasattr(page, 'client_storage'): # Example: clear from client storage
                 page.client_storage.remove("current_user_id") # type: ignore

            router.navigate_to(LOGIN_ROUTE)

        actions.append(
            ft.IconButton(
                icon=ft.Icons.LOGOUT,
                tooltip="Logout",
                icon_color=ft.Colors.WHITE,
                on_click=logout,
            )
        )

    return ft.AppBar(
        leading=leading_widget,
        leading_width=70 if leading_widget else None,
        title=ft.Text(title_text),
        bgcolor=ft.Colors.BLUE_700, # Consistent AppBar color
        color=ft.Colors.WHITE,
        actions=actions if actions else None,
    )

```

```python
# Filename: app/ui/components/common/dialog_factory.py
from typing import Callable, List, Optional
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
```

```python
# Filename: app/ui/components/common/search_bar_component.py
import threading
from typing import Callable
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
```

```python
# Filename: app/ui/components/common/paginated_data_table.py
from math import ceil
from typing import List, Callable, Optional, Any, Dict, TypeVar, Generic
import flet as ft
import datetime

from app.data.database import get_db_session # For default db session

# Define a generic type for the data items
T = TypeVar('T')

class PaginatedDataTable(ft.Container, Generic[T]):
    def __init__(
        self,
        page: ft.Page,
        # Function to fetch all data. Takes a db session.
        fetch_all_data_func: Callable[[Any], List[T]],
        # List of column definitions. Each dict should have:
        # 'key': attribute name in the data item T
        # 'label': string for the column header
        # 'sortable': bool, if the column can be sorted
        # 'numeric': bool, for ft.DataColumn numeric property
        # 'display_formatter': Optional Callable[[Any, T], ft.Control] or Callable[[Any], ft.Control]
        #                      to format the cell content. Receives raw value and optionally the full item.
        #                      Defaults to ft.Text(str(value)).
        # 'searchable': bool, if this column's value should be included in default search
        column_definitions: List[Dict[str, Any]],
        # Function to build the actions ft.DataCell for a row. Receives item T.
        action_cell_builder: Optional[Callable[[T, PaginatedDataTable], ft.DataCell]], # Pass self for page access
        rows_per_page: int = 10,
        initial_sort_key: Optional[str] = None, # Key from column_definitions
        initial_sort_ascending: bool = True,
        on_data_stats_changed: Optional[Callable[[int, int, int], None]] = None, # total, active, expired (example)
                                                                                  # Or a more generic stats callback
        no_data_message: str = "No data available.",
        card_elevation: float = 2,
        card_padding: int = 15,
        heading_row_height: int = 40,
        data_row_max_height: int = 48,
        default_search_enabled: bool = True,
        show_pagination: bool = True,
        **kwargs
    ):
        super().__init__(expand=True, padding=ft.padding.symmetric(horizontal=5), **kwargs)
        self.page = page
        self.fetch_all_data_func = fetch_all_data_func
        self.column_definitions = column_definitions
        self.action_cell_builder = action_cell_builder
        self.rows_per_page = rows_per_page
        self.on_data_stats_changed = on_data_stats_changed
        self.no_data_message = no_data_message
        self.default_search_enabled = default_search_enabled
        self.show_pagination = show_pagination

        self._all_unfiltered_data: List[T] = []
        self._displayed_data: List[T] = [] # Filtered and sorted data

        self._current_sort_column_key: Optional[str] = initial_sort_key
        self._current_sort_ascending: bool = initial_sort_ascending
        self._current_page_number: int = 1
        self._last_search_term: str = ""

        self.datatable = ft.DataTable(
            columns=[], # Will be populated by _initialize_columns
            rows=[],
            column_spacing=20,
            expand=True,
            vertical_lines=ft.BorderSide(width=0.5, color=ft.Colors.with_opacity(0.15, ft.Colors.ON_SURFACE)),
            horizontal_lines=ft.BorderSide(width=0.5, color=ft.Colors.with_opacity(0.1, ft.Colors.ON_SURFACE)),
            sort_ascending=self._current_sort_ascending,
            # sort_column_index will be set dynamically if a sort_key is found
            heading_row_height=heading_row_height,
            data_row_max_height=data_row_max_height,
        )
        self._initialize_columns() # Set sort_column_index here

        self.prev_button = ft.IconButton(
            ft.Icons.KEYBOARD_ARROW_LEFT_ROUNDED, on_click=self._prev_page, tooltip="Previous Page", disabled=True
        )
        self.next_button = ft.IconButton(
            ft.Icons.KEYBOARD_ARROW_RIGHT_ROUNDED, on_click=self._next_page, tooltip="Next Page", disabled=True
        )
        self.page_info_text = ft.Text(
            f"Page {self._current_page_number} of 1",
            weight=ft.FontWeight.W_500, color=ft.Colors.ON_SURFACE_VARIANT
        )

        pagination_controls_row = ft.Row(
            [self.prev_button, self.page_info_text, self.next_button],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
            visible=self.show_pagination
        )

        table_with_pagination_column = ft.Column(
            [
                ft.Container(content=self.datatable, expand=True, padding=ft.padding.only(bottom=10)),
                pagination_controls_row
            ],
            expand=True, spacing=5
        )

        self.content = ft.Card(
            content=ft.Container(
                content=table_with_pagination_column,
                padding=card_padding,
                border_radius=8
            ),
            elevation=card_elevation,
        )
        # self.refresh_data_and_ui() # Initial data load called by consumer typically

    def _get_column_def_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        for col_def in self.column_definitions:
            if col_def['key'] == key:
                return col_def
        return None

    def _get_column_index_by_key(self, key: str) -> Optional[int]:
        for i, col_def in enumerate(self.column_definitions):
            if col_def['key'] == key:
                return i
        return None

    def _initialize_columns(self):
        ft_columns: List[ft.DataColumn] = []
        for i, col_def in enumerate(self.column_definitions):
            ft_columns.append(
                ft.DataColumn(
                    ft.Text(col_def['label'], weight=ft.FontWeight.BOLD, size=13),
                    numeric=col_def.get('numeric', False),
                    on_sort=self._handle_column_sort if col_def.get('sortable', False) else None,
                )
            )
        if self.action_cell_builder:
            ft_columns.append(ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.BOLD, size=13), numeric=True))

        self.datatable.columns = ft_columns

        if self._current_sort_column_key:
            idx = self._get_column_index_by_key(self._current_sort_column_key)
            if idx is not None:
                self.datatable.sort_column_index = idx
            else: # sort key not found in columns, reset
                self._current_sort_column_key = None


    def _handle_column_sort(self, e: ft.ControlEvent):
        # Determine which column was clicked based on the label or a more robust ID
        # For simplicity, we find by label, assuming labels are unique for sortable columns
        clicked_label_widget = e.control.label
        if not isinstance(clicked_label_widget, ft.Text): return
        clicked_label = clicked_label_widget.value

        clicked_col_key = None
        clicked_col_idx = -1

        for i, col_def in enumerate(self.column_definitions):
            if col_def['label'] == clicked_label and col_def.get('sortable', False):
                clicked_col_key = col_def['key']
                clicked_col_idx = i
                break

        if clicked_col_key:
            if self._current_sort_column_key == clicked_col_key:
                self._current_sort_ascending = not self._current_sort_ascending
            else:
                self._current_sort_column_key = clicked_col_key
                self._current_sort_ascending = True

            self.datatable.sort_column_index = clicked_col_idx
            self.datatable.sort_ascending = self._current_sort_ascending
            self._current_page_number = 1
            self._filter_and_sort_displayed_data(self._last_search_term) # Re-sort and update UI
        else:
            print(f"Warning: Sort key not found for column label '{clicked_label}'")


    def _get_sort_value_for_item(self, item: T, sort_key: str) -> Any:
        """
        Extracts a value from an item for sorting.
        Can be overridden by subclasses for complex sorting logic.
        """
        col_def = self._get_column_def_by_key(sort_key)
        raw_value = getattr(item, sort_key, None)

        if col_def and col_def.get('custom_sort_value_getter'):
            return col_def['custom_sort_value_getter'](item)

        if isinstance(raw_value, str):
            return raw_value.lower()
        if raw_value is None: # Consistent handling for None values
            # Adjust for specific types like datetime if needed
            if isinstance(getattr(item, sort_key, None), datetime.datetime): # Check original type
                 return datetime.datetime.min if self._current_sort_ascending else datetime.datetime.max
            return float('-inf') if self._current_sort_ascending else float('inf')
        return raw_value


    def _filter_and_sort_displayed_data(self, search_term: str = ""):
        self._last_search_term = search_term.lower().strip()

        if not self._last_search_term or not self.default_search_enabled:
            self._displayed_data = list(self._all_unfiltered_data)
        else:
            self._displayed_data = []
            searchable_keys = [cd['key'] for cd in self.column_definitions if cd.get('searchable', True)] # Default to searchable
            for item in self._all_unfiltered_data:
                found = False
                for key in searchable_keys:
                    value = getattr(item, key, None)
                    display_formatter = self._get_column_def_by_key(key).get('display_formatter') # type: ignore
                    
                    str_value = ""
                    if display_formatter:
                        # Attempt to get a string representation if formatter returns a Control
                        # This is a simplification; complex formatters might need specific string extractors.
                        formatted_control = display_formatter(value, item) if callable(display_formatter) and display_formatter.__code__.co_argcount == 2 else display_formatter(value) # type: ignore
                        if isinstance(formatted_control, ft.Text):
                            str_value = str(formatted_control.value).lower()
                        elif value is not None:
                             str_value = str(value).lower()
                    elif value is not None:
                        str_value = str(value).lower()

                    if self._last_search_term in str_value:
                        found = True
                        break
                if found:
                    self._displayed_data.append(item)
        
        # Sorting
        if self._current_sort_column_key:
            sort_key_attr = self._current_sort_column_key
            self._displayed_data.sort(
                key=lambda item: self._get_sort_value_for_item(item, sort_key_attr),
                reverse=not self._current_sort_ascending
            )
        self._update_datatable_rows()


    def _build_datarow(self, item: T) -> ft.DataRow:
        cells: List[ft.DataCell] = []
        for col_def in self.column_definitions:
            key = col_def['key']
            raw_value = getattr(item, key, None)
            formatter = col_def.get('display_formatter')

            cell_content: ft.Control
            if formatter:
                # Check if formatter expects the full item or just the value
                try:
                    if callable(formatter) and formatter.__code__.co_argcount == 2: #expects value, item
                        cell_content = formatter(raw_value, item)
                    else: # expects only value
                        cell_content = formatter(raw_value)
                except Exception as e:
                    # print(f"Error applying formatter for key {key}: {e}")
                    cell_content = ft.Text(str(raw_value) if raw_value is not None else "", size=12.5)
            else:
                cell_content = ft.Text(str(raw_value) if raw_value is not None else "", size=12.5)
            cells.append(ft.DataCell(cell_content))

        if self.action_cell_builder:
            action_cell = self.action_cell_builder(item, self) # Pass self (the table instance)
            cells.append(action_cell)
        
        return ft.DataRow(cells=cells, color={"hovered": ft.Colors.with_opacity(0.05, ft.Colors.PRIMARY)})


    def _update_datatable_rows(self):
        if not self._displayed_data:
            self.datatable.rows = [ft.DataRow([ft.DataCell(ft.Text(self.no_data_message, italic=True), colspan=len(self.datatable.columns))])] # type: ignore
        else:
            start_index = (self._current_page_number - 1) * self.rows_per_page
            end_index = start_index + self.rows_per_page
            paginated_items = self._displayed_data[start_index:end_index]
            self.datatable.rows = [self._build_datarow(item) for item in paginated_items]

        self._update_pagination_controls()
        if self.page: self.page.update()


    def _update_pagination_controls(self):
        if not self.page_info_text.page or not self.show_pagination: # Check if control is on page
            return

        total_rows = len(self._displayed_data)
        total_pages = ceil(total_rows / self.rows_per_page) if total_rows > 0 else 1
        total_pages = max(1, total_pages) # Ensure at least 1 page

        self.page_info_text.value = f"Page {self._current_page_number} of {total_pages}"
        self.prev_button.disabled = self._current_page_number == 1
        self.next_button.disabled = self._current_page_number == total_pages

        # No individual updates, rely on page.update() in _update_datatable_rows

    def _prev_page(self, e):
        if self._current_page_number > 1:
            self._current_page_number -= 1
            self._update_datatable_rows()

    def _next_page(self, e):
        total_rows = len(self._displayed_data)
        total_pages = ceil(total_rows / self.rows_per_page) if total_rows > 0 else 1
        if self._current_page_number < total_pages:
            self._current_page_number += 1
            self._update_datatable_rows()

    def refresh_data_and_ui(self, search_term: Optional[str] = None):
        """Fetches all data, then filters, sorts, and updates the UI."""
        if search_term is None: # Use last known search term if none provided
            search_term = self._last_search_term
        else: # Update last known search term if new one is provided
            self._last_search_term = search_term

        try:
            with get_db_session() as db:
                self._all_unfiltered_data = self.fetch_all_data_func(db)
            
            # If a stats callback is provided, call it with unfiltered data stats
            if self.on_data_stats_changed:
                # This part needs to be generic or configurable for what stats to compute.
                # Example: total, active, expired for Games.
                # For now, let's assume a simple total count.
                # Subclasses can override this or on_data_stats_changed can be made more flexible.
                # For GamesTable specifically, we'll handle its active/expired count in the subclass or adapter.
                total_count = len(self._all_unfiltered_data)
                # A more generic stats calculation would require more info or a specific callback.
                # self.on_data_stats_changed(total_count, 0, 0) # Placeholder
                # For now, let the specific table (GamesTable) trigger its specific on_data_changed.

            self._current_page_number = 1 # Reset to first page
            self._filter_and_sort_displayed_data(search_term)

        except Exception as e:
            print(f"Error refreshing data for table: {e}")
            if self.page:
                self.page.open(ft.SnackBar(ft.Text(f"Error loading data: {type(e).__name__}"), open=True, bgcolor=ft.Colors.ERROR))


    def get_current_search_term(self) -> str:
        return self._last_search_term

    def close_dialog_and_refresh(self, dialog_to_close: Optional[ft.AlertDialog] = None, success_message: Optional[str] = None):
        """Helper to close a dialog (if provided) and refresh table data."""
        if dialog_to_close and self.page.dialog == dialog_to_close:
            self.page.close(dialog_to_close)
            # self.page.dialog = None # Let caller manage this if needed, e.g. if dialog is instance var
        if success_message and self.page:
            self.page.open(ft.SnackBar(ft.Text(success_message), open=True))
        self.refresh_data_and_ui(self._last_search_term)

    def show_error_snackbar(self, message: str):
        if self.page:
            self.page.open(ft.SnackBar(ft.Text(message), open=True, bgcolor=ft.Colors.ERROR))

```

Now, I will refactor the existing files to use these new common components. This will be a multi-step process. I'll start with `app/ui/views/login_view.py` to use `appbar_factory.py`.

```python
# Filename: app/config.py
from pathlib import Path

# Database Configuration
DB_FILENAME = "lottery_manager.db"
DB_BASE_DIR = Path("db_data")  # Renamed for clarity
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_BASE_DIR.joinpath(DB_FILENAME)}"

# Application Settings
APP_TITLE = "Lottery Manager"
DEFAULT_THEME_MODE = "light" # "light" or "dark"

# Sales Person Info
SALES_PERSON_USERNAME = "sales"
SALES_PERSON_PASSWORD = "admin123"

# -------- File Separator --------

# Filename: app/constants.py
ADMIN_ROLE = "admin"
EMPLOYEE_ROLE = "employee"
SALESPERSON_ROLE = "salesperson"

ALL_USER_ROLES = [ADMIN_ROLE, EMPLOYEE_ROLE, SALESPERSON_ROLE]
# Roles that can be typically managed (created/edited by an admin/salesperson)
MANAGED_USER_ROLES = [ADMIN_ROLE, EMPLOYEE_ROLE]

# Ticket orders
REVERSE_TICKET_ORDER = "reverse"
FORWARD_TICKET_ORDER = "forward"


# Route Names
LOGIN_ROUTE = "login"
ADMIN_DASHBOARD_ROUTE = "admin_dashboard"
EMPLOYEE_DASHBOARD_ROUTE = "employee_dashboard"
SALESPERSON_DASHBOARD_ROUTE = "salesperson_dashboard"

# Game Management routes
GAME_MANAGEMENT_ROUTE = "game_management"

# Book management routes
BOOK_MANAGEMENT_ROUTE = "book_management"

# -------- File Separator --------

# Filename: app/main.py
import flet as ft
from app.ui.router import Router
from app.data.database import init_db
from app.constants import LOGIN_ROUTE
from app.config import APP_TITLE, DEFAULT_THEME_MODE

def main(page: ft.Page):
    # Configure page
    page.title = APP_TITLE

    page.window.maximized = True

    # Define a Material 3 theme
    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.BLUE_GREY, # You can change this seed color (e.g., INDIGO, TEAL)
        use_material3=True,
    )

    if DEFAULT_THEME_MODE.lower() == "dark":
        page.theme_mode = ft.ThemeMode.DARK
    else:
        page.theme_mode = ft.ThemeMode.LIGHT

    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    init_db()
    router = Router(page)
    router.navigate_to(LOGIN_ROUTE) # Initial navigation
    # page.update() # Router's navigate_to should handle updates. Redundant here.

if __name__ == "__main__":
    ft.app(target=main)

# -------- File Separator --------

# Filename: app/__init__.py


# -------- File Separator --------

# Filename: app/core/exceptions.py
class AppException(Exception):
    """Base exception class for the application."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

class AuthenticationError(AppException):
    """Raised for authentication failures (e.g., invalid credentials, user not found for login)."""
    pass

class UserNotFoundError(AppException):
    """Raised when a specific user is expected but not found (e.g., when updating/deleting by ID)."""
    pass

class GameNotFoundError(AppException):
    """Raised when a specific game is expected but not found (e.g., when updating/deleting by ID)."""
    pass

class ValidationError(AppException):
    """Raised for data validation errors (e.g., missing fields, invalid format)."""
    pass

class DatabaseError(AppException):
    """Raised for errors during database operations (e.g., integrity constraints, connection issues)."""
    pass

class WidgetError(AppException):
    """Raised for errors during widget operations (e.g., invalid state, invalid configuration)."""
    pass


# -------- File Separator --------

# Filename: app/core/models.py
"""
Defines the SQLAlchemy models for the application.

This module contains the database schema definitions using SQLAlchemy's
declarative base. It includes the `User`, `Game`, `Book`,
and `SalesEntry` models.
"""
import bcrypt
import datetime # Ensure datetime is imported
from sqlalchemy import String, Integer, Column, ForeignKey, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from app.constants import REVERSE_TICKET_ORDER

Base = declarative_base()

class User(Base):
    """
    Represents a user in the system.

    Attributes:
        id (int): The primary key for the user.
        username (str): The unique username for the user.
        password (str): The hashed password for the user.
        role (str): The role of the user (e.g., "employee", "admin").
                    Defaults to "employee".
        created_date (DateTime): The date and time when the user was created.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="employee")
    created_date = Column(DateTime, nullable=False, default=datetime.datetime.now) # Corrected: Use datetime.datetime.now
    is_active = Column(Boolean, nullable=False, default=True)

    def set_password(self, plain_password: str):
        """
        Hashes the plain password using bcrypt and stores it.

        Args:
            plain_password (str): The plain text password to hash.
        """
        password_bytes = plain_password.encode('utf-8')
        salt = bcrypt.gensalt()
        self.password = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

    def check_password(self, plain_password: str) -> bool:
        """
        Verifies a plain password against the stored hashed password.

        Args:
            plain_password (str): The plain text password to verify.

        Returns:
            bool: True if the password matches, False otherwise.
        """
        if not self.password:
            return False
        password_bytes = plain_password.encode('utf-8')
        hashed_password_bytes = self.password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_password_bytes)

    def __repr__(self):
        """
        Returns a string representation of the User object.
        """
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"

class Game(Base):
    """
    Represents a game in the system.

    Attributes:
        id (int): The primary key for the game.
        name (str): The unique name of the game.
        price (int): The price of one ticket for the game (in cents).
        total_tickets (int): The total number of tickets available for this game type.
        books (relationship): A list of book associated with this game.
        series_number (int, optional): An optional series number for the game.
        default_ticket_order (str, optional): The default order of tickets (e.g., "reverse", "forward").
    """
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False, unique=False)
    price = Column(Integer, nullable=False) # Price in cents
    total_tickets = Column(Integer, nullable=False)
    is_expired = Column(Boolean, nullable=False, default=False)
    default_ticket_order = Column(String, nullable=False, default=REVERSE_TICKET_ORDER)
    created_date = Column(DateTime, nullable=False, default=datetime.datetime.now) # Corrected
    expired_date = Column(DateTime, nullable=True)

    books = relationship("Book", back_populates="game")
    game_number = Column(Integer, nullable=False, unique=True)

    @property
    def calculated_total_value(self) -> int: # In cents
        return (self.price * self.total_tickets) if self.price is not None and self.total_tickets is not None else 0


    def __repr__(self):
        """
        Returns a string representation of the game object.
        """
        return f"<Game(id={self.id}, name='{self.name}', price={self.price}, total_tickets={self.total_tickets}, game_number={self.game_number}, default_ticket_order='{self.default_ticket_order}', is_expired={self.is_expired})>"

class Book(Base):
    """
    Represents an instance of a book, often a specific print run or batch.

    Attributes:
        id (int): The primary key for the book.
        ticket_order (str): The order of tickets (e.g., "reverse", "forward").
                            Defaults to "reverse".
        is_active (bool): Whether this book is currently active for sales.
                          Defaults to True.
        activate_date (DateTime): The date when this book became active.
        finish_date (DateTime, optional): The date when this book was finished or deactivated.
        game_id (int): Foreign key referencing the `Game` this Book belongs to.
        game (relationship): The `Game` object this Book is associated with.
        sales_entries (relationship): A list of sales entries associated with this book.
        instance_number (int, optional): An optional instance number for this book.
    """
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticket_order = Column(String, nullable=False) # Will be set based on game if not provided
    is_active = Column(Boolean, nullable=False, default=True)
    activate_date = Column(DateTime, nullable=False, default=datetime.datetime.now) # Corrected
    finish_date = Column(DateTime, nullable=True)
    current_ticket_number = Column(Integer, nullable=False)

    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    game = relationship("Game", back_populates="books")

    sales_entries = relationship("SalesEntry", back_populates="book")
    book_number = Column(Integer, nullable=False) # Should this be unique per game?

    def __init__(self, **kwargs):
        """
        Initializes a new Book instance.
        Sets default ticket_order from the game if not specified.
        Sets initial current_ticket_number based on order and game's total_tickets.
        """
        # Ensure 'game' is resolved if 'game_id' is passed, or 'game' object itself
        # This logic is usually handled by SQLAlchemy relationships after the object is added to a session.
        # For __init__, we rely on 'game' being passed or correctly set up by the caller if needed immediately.
        
        super().__init__(**kwargs) # Initialize SQLAlchemy mapped attributes

        if 'ticket_order' not in kwargs and self.game:
             self.ticket_order = self.game.default_ticket_order
        elif 'ticket_order' not in kwargs and not self.game:
            # This case is problematic; ticket_order depends on the game.
            # Ensure game is associated before or during Book creation.
            # For now, we might need to defer this or ensure game is always present.
            # Or set a temporary default if game is not yet known, though not ideal.
            # Let's assume self.game will be available or ticket_order is explicitly passed.
            pass


        # Initialize current_ticket_number. This needs self.game to be populated.
        # This might be better handled in a post-init hook or after association if game is not available in __init__.
        # If game object (self.game) is available (e.g., passed in kwargs or set by relationship before commit)
        if self.game:
            if self.ticket_order == REVERSE_TICKET_ORDER:
                self.current_ticket_number = self.game.total_tickets
            else: # FORWARD_TICKET_ORDER
                self.current_ticket_number = 0
        # else:
            # If self.game is not yet set, current_ticket_number might not be correctly initialized here.
            # This could be an issue if the object is used before being fully associated and flushed.
            # One approach: if game_id is provided, the caller must ensure the game exists and handle this logic.
            # Another: rely on SQLAlchemy to load `self.game` if `game_id` is set, but that's usually after session add.
            # For now, the original logic is preserved, assuming self.game is available.


    def __repr__(self):
        """
        Returns a string representation of the BookInstance object.
        """
        return f"<Book(id={self.id}, game_id={self.game_id}, ticket_order='{self.ticket_order}', is_active={self.is_active}, activate_date={self.activate_date}, finish_date={self.finish_date})>"

class SalesEntry(Base):
    """
    Represents a sales entry for a book instance.

    Attributes:
        id (int): The primary key for the sales entry.
        start_number (int): The starting ticket number for this sale.
        end_number (int): The ending ticket number for this sale.
        date (DateTime): The date of the sale.
        count (int): The number of tickets sold in this entry.
                     Calculated based on start_number, end_number, and ticket_order.
        price (int): The total price for this sales entry (in cents).
                     Calculated based on count and book price.
        book_id (int): Foreign key referencing the `Book` of this sale.
        book (relationship): The `Book` object associated with this sale.
        user_id (int): Foreign key referencing the `User` who made this sale.
        user (relationship): The `User` object associated with this sale.
    """
    __tablename__ = "sales_entries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    start_number = Column(Integer, nullable=False)
    end_number = Column(Integer, nullable=False)
    date = Column(DateTime, nullable=False, default=datetime.datetime.now) # Corrected
    count = Column(Integer, nullable=False) # This will be calculated
    price = Column(Integer, nullable=False) # This will be calculated (in cents)

    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    book = relationship("Book", back_populates="sales_entries")

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User") # No back_populates needed if User doesn't link back to SalesEntry list

    def calculate_count_and_price(self):
        """
        Calculates and sets the 'count' and 'price' for this sales entry.
        Price is stored in cents.
        This method should be called before saving the sales entry if
        'count' and 'price' are not manually set.
        """
        if self.book and self.book.game:
            if self.book.ticket_order == REVERSE_TICKET_ORDER:
                self.count = self.start_number - self.end_number
            else: # Assuming "forward" or any other order implies end_number > start_number
                self.count = self.end_number - self.start_number
            self.price = self.count * self.book.game.price # game.price is in cents
        else:
            self.count = 0
            self.price = 0

    def __repr__(self):
        """
        Returns a string representation of the SalesEntry object.
        """
        return f"<SalesEntry(id={self.id}, book_id={self.book_id}, user_id={self.user_id}, start_number={self.start_number}, end_number={self.end_number}, date={self.date}, count={self.count}, price={self.price})>"

class License(Base):
    __tablename__ = "license"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    is_active = Column(Boolean, nullable=False, default=False)

    def set_status(self, status: bool):
        self.is_active = status

    def __repr__(self):
        return f"<License(id={self.id}, is_active={self.is_active})>"


# -------- File Separator --------

# Filename: app/core/__init__.py
from .exceptions import (
    AppException,
    AuthenticationError,
    UserNotFoundError,
    GameNotFoundError, # Added missing GameNotFoundError
    ValidationError,
    DatabaseError,
    WidgetError
)

# -------- File Separator --------

# Filename: app/data/crud_games.py
from sqlalchemy.orm import Session # Added Session import
from sqlalchemy.exc import IntegrityError
from app.core.models import Game
from app.core.exceptions import DatabaseError, ValidationError, GameNotFoundError # Import custom exceptions


def get_game_by_game_number(db: Session, game_number: int) -> Game | None: # Type hint for game_number
    return db.query(Game).filter(Game.game_number == game_number).first()


def create_game(db: Session, game_name: str, price: int, total_tickets: int, game_number: int, order: str) -> Game: # price is int (cents)
    if not game_name:
        raise ValidationError("Game Name is required for creating a Game.")
    if price is None or price < 0: # price can be 0 for free games, but not negative
        raise ValidationError("Price is required and cannot be negative for creating a Game.")
    if not total_tickets or total_tickets <= 0:
        raise ValidationError("Total Tickets must be a positive number for creating a Game.")
    if not game_number or game_number <=0:
        raise ValidationError("Game Number must be a positive number for creating a Game.")
    if not order:
        raise ValidationError("Order is required for creating a Game.")

    existing_game = get_game_by_game_number(db, game_number)
    if existing_game:
        raise DatabaseError(f"Game with game number '{game_number}' already exists.")

    try:
        game = Game(
            name=game_name,
            price=price, # Expecting price in cents
            total_tickets=total_tickets,
            default_ticket_order=order,
            game_number=game_number,
        )
        db.add(game)
        db.commit()
        db.refresh(game)
        return game
    except IntegrityError as e: # Should be caught by pre-check, but as a fallback
        db.rollback()
        raise DatabaseError(f"Database threw an IntegrityError when adding new Game: {e.orig}") # Access original error
    except Exception as e:
        db.rollback()
        # Log the original exception e for debugging
        raise DatabaseError(f"Could not create game '{game_name}': An unexpected error occurred: {e}")


def get_all_games_sort_by_expiration_prices(db: Session) -> list[Game]: # Added Session type hint
    # Default sort: Active games first, then by price (low to high), then by game_number (low to high)
    return db.query(Game).order_by(Game.is_expired, Game.price, Game.game_number).all()


def get_game_by_id(db: Session, game_id: int) -> Game | None: # Added Session type hint and return None
    return db.query(Game).filter(Game.id == game_id).first()

def expire_game_in_db(db: Session, game_id: int) -> Game | None:
    game = get_game_by_id(db, game_id)
    if not game:
        raise GameNotFoundError(f"Game with ID {game_id} not found.")
    if game.is_expired: # Already expired
        return game

    game.is_expired = True
    game.expired_date = datetime.datetime.now() # Corrected: Use datetime.datetime.now

    # Deactivate all associated books
    for book in game.books:
        if book.is_active:
            book.is_active = False
            # Optionally set book.finish_date = datetime.datetime.now() if that's desired
            # book.finish_date = datetime.datetime.now()
    try:
        db.commit()
        db.refresh(game)
        return game
    except Exception as e:
        db.rollback()
        raise DatabaseError(f"Could not expire game {game_id}: {e}")


def reactivate_game_in_db(db: Session, game_id: int) -> Game | None:
    game = get_game_by_id(db, game_id)
    if not game:
        raise GameNotFoundError(f"Game with ID {game_id} not found.")
    if not game.is_expired: # Already active
        return game

    game.is_expired = False
    game.expired_date = None
    # Note: Reactivating a game does NOT automatically reactivate its books.
    # This should be a conscious decision by the user in the UI for specific books.
    try:
        db.commit()
        db.refresh(game)
        return game
    except Exception as e:
        db.rollback()
        raise DatabaseError(f"Could not reactivate game {game_id}: {e}")

# -------- File Separator --------

# Filename: app/data/crud_license.py
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.models import License
from app.core.exceptions import DatabaseError # Import custom exception


def crud_create_license(db: Session, license_is_active: bool = False) -> License: # Renamed license to license_is_active
    """
    Creates a new license record.
    Raises DatabaseError if a license already exists or on other DB issues.
    """
    # This check might be redundant if we expect only one license record controlled by its existence.
    # If the intention is truly to prevent creating a *second* record, this is fine.
    # If it's about "find or create", the logic in services is better.
    if db.query(License).first():
        # Original code returned existing, but this function is crud_CREATE_license.
        # Raising an error if it already exists seems more aligned with "create" semantics
        # or the calling code should check first.
        # For now, aligning with original behavior to return existing if trying to create when one exists.
        # However, the original also had a potential conflict if it tried to create one
        # after this check passed but before commit (race condition, though unlikely for license).
        # The service layer handles "get or create" more robustly.
        # This function will now strictly attempt to create, raising error if it exists.
        # Let's revert to original behavior: if one exists, return it, as this is what crud_set_license_status relied on.
         return db.query(License).first() # type: ignore

    try:
        new_license = License(is_active=license_is_active)
        db.add(new_license)
        db.commit()
        db.refresh(new_license)
        return new_license
    except IntegrityError:
        db.rollback()
        # This path should ideally not be hit if the check above is effective,
        # but good as a safeguard for concurrent operations.
        raise DatabaseError("License record creation failed due to a conflict (e.g. already exists).")
    except Exception as e:
        db.rollback()
        raise DatabaseError(f"Could not create license: An unexpected error occurred: {e}")


def crud_get_license(db: Session) -> License | None:
    """Retrieves the first license record."""
    return db.query(License).first()


def crud_get_license_status(db: Session) -> bool:
    """Retrieves the active status of the first license record."""
    license_record = db.query(License).first()
    return license_record.is_active if license_record else False


def crud_set_license_status(db: Session, license_activated: bool) -> License | None:
    """Sets the active status of the first license record. Creates one if none exists."""
    license_record = db.query(License).first()

    if not license_record:
        # This part was problematic. crud_create_license might return an existing license
        # or create a new one. We need to ensure we are operating on the correct instance.
        # The LicenseService handles the "create if not exists" logic more cleanly.
        # For this CRUD function, we assume it operates on an existing license or fails.
        # Let the service layer handle creation. If called directly, it should find one.
        # However, the original code implies it *can* create.
        # To maintain that, but make it safer:
        try:
            license_record = License(is_active=license_activated) # Create with the desired status
            db.add(license_record)
            # No commit yet, will be committed below.
        except Exception as e: # Broad exception for creation attempt
            db.rollback()
            raise DatabaseError(f"Could not create new license during update: {e}")
    else:
        license_record.set_status(license_activated)

    try:
        db.commit() # Commit changes (either new record or updated status)
        if license_record:  # Ensure license_record is not None before refresh
             db.refresh(license_record)
        return license_record
    except Exception as e:
        db.rollback()
        raise DatabaseError(f"Could not update license status: An unexpected error occurred: {e}")


# -------- File Separator --------

# Filename: app/data/crud_users.py
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List, Type

from app.core.models import User
from app.constants import EMPLOYEE_ROLE # Use constant
from app.core.exceptions import UserNotFoundError, DatabaseError, ValidationError # Import custom exceptions

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

def get_users_by_roles(db: Session, roles: List[str]) -> List[User]: # Return List[User]
    return db.query(User).filter(User.role.in_(roles)).order_by(User.username).all() # Added ordering

def get_all_users(db: Session) -> List[User]: # Return List[User]
    return db.query(User).order_by(User.username).all() # Added ordering


def create_user(db: Session, username: str, password: str, role: str = EMPLOYEE_ROLE) -> User:
    """
    Create a new user.
    Raises:
        ValidationError: If username or password is not provided.
        DatabaseError: If the user could not be created (e.g., username exists).
    """
    if not username:
        raise ValidationError("Username is required for creating a user.")
    if not password: # Password validation (e.g. length) should be in service or model if complex
        raise ValidationError("Password is required for creating a user.")
    if not role:
        raise ValidationError("Role is required for creating a user.")


    existing_user = get_user_by_username(db, username)
    if existing_user:
        raise DatabaseError(f"User with username '{username}' already exists.")

    try:
        # created_date is handled by SQLAlchemy model default
        user = User(username=username, role=role)
        user.set_password(password) # Hash password
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError: # Should be caught by pre-check, but as a fallback
        db.rollback()
        # This typically means username unique constraint was violated by a concurrent transaction
        raise DatabaseError(f"User with username '{username}' already exists (IntegrityError).")
    except Exception as e:
        db.rollback()
        # Log the original exception e for debugging
        raise DatabaseError(f"Could not create user '{username}': An unexpected error occurred: {e}")


def update_user(db: Session, user_id: int, username: Optional[str] = None,
                password: Optional[str] = None, role: Optional[str] = None, is_active: Optional[bool] = None) -> User:
    """
    Update a user. Can also update is_active status.
    Raises:
        UserNotFoundError: If the user with user_id is not found.
        DatabaseError: If the update fails.
        ValidationError: If new username is empty (if provided).
    """
    user = get_user_by_id(db, user_id)
    if not user:
        raise UserNotFoundError(f"User with ID {user_id} not found.")

    updated = False
    try:
        if username is not None:
            if not username.strip():
                raise ValidationError("Username cannot be empty.")
            # Check if new username already exists for another user
            if username != user.username and db.query(User).filter(User.username == username, User.id != user_id).first():
                raise DatabaseError(f"Username '{username}' is already taken by another user.")
            user.username = username
            updated = True
        if password: # Only update password if a new one is provided and not empty
            user.set_password(password)
            updated = True
        if role:
            user.role = role
            updated = True
        if is_active is not None:
            user.is_active = is_active
            updated = True

        if updated:
            db.commit()
            db.refresh(user)
        return user
    except IntegrityError: # e.g. if unique constraint on username violated by concurrent transaction
        db.rollback()
        # username check should ideally prevent this, but good to have
        raise DatabaseError(f"Could not update user {user.username}: Username conflict (IntegrityError).")
    except Exception as e:
        db.rollback()
        raise DatabaseError(f"Could not update user {user.username}: An unexpected error occurred: {e}")


def delete_user(db: Session, user_id: int) -> bool:
    """
    Delete a user.
    Raises:
        UserNotFoundError: If the user with user_id is not found.
        DatabaseError: If deletion fails.
    """
    user = get_user_by_id(db, user_id)
    if not user:
        raise UserNotFoundError(f"User with ID {user_id} not found.")
    try:
        username_deleted = user.username # For logging or messages
        db.delete(user)
        db.commit()
        print(f"User '{username_deleted}' (ID: {user_id}) deleted successfully.") # Keep for now, or use logging
        return True
    except Exception as e:
        db.rollback()
        raise DatabaseError(f"Could not delete user with ID {user_id}: An unexpected error occurred: {e}")

def any_users_exist(db: Session) -> bool:
    return db.query(User.id).first() is not None # Query for id is slightly more efficient


# -------- File Separator --------

# Filename: app/data/database.py
from typing import Any, Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

from app.constants import SALESPERSON_ROLE, ADMIN_ROLE
from app.core.models import Base
from app.config import SQLALCHEMY_DATABASE_URL, DB_BASE_DIR, SALES_PERSON_USERNAME, SALES_PERSON_PASSWORD
from app.services import UserService # Direct import for initialization
from app.services.license_service import LicenseService # Direct import


# Ensure the database directory exists
DB_BASE_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}, # Required for SQLite with Flet/FastAPI
)

# expire_on_commit=False is important for Flet so objects accessed after commit are still usable
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

@contextmanager
def get_db_session() -> Generator[Session, Any, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit() # Commit successful operations
    except Exception:
        db.rollback() # Rollback on any error
        raise # Re-raise the exception so it can be handled upstream
    finally:
        db.close()

def init_db():
    print(f"Initializing database at: {SQLALCHEMY_DATABASE_URL}")
    Base.metadata.create_all(bind=engine, checkfirst=True) # checkfirst is good practice
    print("Database tables checked/created.")
    try:
        with get_db_session() as db:
            run_initialization_script(db)
            print("Initialization script completed.")
    except Exception as e:
        print(f"Error during database initialization script: {e}")
        # Depending on the severity, you might want to exit or handle this
        raise


def run_initialization_script(db: Session):
    # TODO : FIX THIS IN FINAL PRODUCT (REMOVE ADMIN CREATION AND LICENSE TO FALSE, CHANGE SALES PASSWORD TOO)
    license_service = LicenseService()
    users_service = UserService()

    # Create Salesperson and Admin only if no users exist at all
    if not users_service.any_users_exist(db): # Changed from check_users_exist to any_users_exist
        print("Running for first time. Populating Sales User Info...")
        users_service.create_user(db, SALES_PERSON_USERNAME, SALES_PERSON_PASSWORD, SALESPERSON_ROLE)
        print("Sales User Info populated.")
        # Create a default admin user
        users_service.create_user(db, "admin", SALES_PERSON_PASSWORD, ADMIN_ROLE) # Using the same password for now
        print("Default admin user created.")

    # Ensure a license record exists, default to True (active) for development as per original
    if not license_service.get_license(db):
        print("Creating initial license record (active for dev)...")
        license_service.create_license_if_not_exists(db, license_is_active=True) # Set to True as per original behavior
        print("Initial license record created.")
    # else: # If license exists, ensure it's active for dev as per original logic
    #     if not license_service.get_license_status(db):
    #         print("Activating existing license for dev...")
    #         license_service.set_license_status(db, True)


# -------- File Separator --------

# Filename: app/data/__init__.py
# This can remain empty or be used for selective imports from crud modules
# e.g., from . import crud_users, crud_games, crud_license

# -------- File Separator --------

# Filename: app/services/auth_service.py
from sqlalchemy.orm import Session

from app.data.crud_users import get_user_by_username # Direct DAO access for this specific need
from app.core.models import User
from app.core.exceptions import AuthenticationError, ValidationError

class AuthService:
    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> User:
        """
        Authenticate a user with username and password.

        Args:
            db (Session): The database session.
            username (str): The username to authenticate.
            password (str): The password to authenticate.

        Returns:
            User: The authenticated user.

        Raises:
            ValidationError: If username or password is not provided.
            AuthenticationError: If authentication fails (invalid username/password or user not found or inactive).
        """
        if not username:
            raise ValidationError("Username is required.") # Consistent error messages

        if not password:
            raise ValidationError("Password is required.") # Consistent error messages

        user = get_user_by_username(db, username)

        if not user:
            # Do not reveal if username exists or not for security.
            raise AuthenticationError("Invalid username or password.")

        if not user.check_password(password):
            raise AuthenticationError("Invalid username or password.")

        if not user.is_active:
            # User exists and password is correct, but account is inactive.
            raise AuthenticationError("User account is not active. Please contact an administrator.")

        return user

    @staticmethod
    def get_user_role(user: User) -> str:
        if not user or not hasattr(user, 'role'):
            raise ValueError("Invalid user object provided.")
        return user.role


# -------- File Separator --------

# Filename: app/services/game_service.py
import datetime

from sqlalchemy.orm import Session

from app.core.models import Game
from app.core.exceptions import ValidationError, GameNotFoundError, DatabaseError
from app.constants import REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER # Added FORWARD_TICKET_ORDER
from app.data import crud_games


class GameService:

    def create_game(self, db: Session, game_name: str, price_cents: int, total_tickets: int, game_number: int, order: str = REVERSE_TICKET_ORDER) -> Game:
        if not game_name: # Basic validation, more complex rules could be here
            raise ValidationError("Game Name is required.")
        if price_cents is None or price_cents < 0:
            raise ValidationError("Price must be a non-negative value.")
        if not total_tickets or total_tickets <= 0:
            raise ValidationError("Total Tickets must be a positive number.")
        if not game_number or game_number <=0:
            raise ValidationError("Game Number must be a positive number.")
        if order not in [REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER]:
            raise ValidationError(f"Invalid ticket order specified: {order}.")

        # crud_games.create_game handles DatabaseError if game_number exists
        return crud_games.create_game(db, game_name, price_cents, total_tickets, game_number, order)

    def get_all_games(self, db: Session) -> list[Game]: # Added Session type hint
        return crud_games.get_all_games_sort_by_expiration_prices(db)

    def get_game_by_id(self, db: Session, game_id: int) -> Game | None: # Added Session type hint
        game = crud_games.get_game_by_id(db, game_id)
        if not game:
            raise GameNotFoundError(f"Game with ID {game_id} not found.")
        return game

    def expire_game(self, db: Session, game_id: int) -> Game:
        game = crud_games.get_game_by_id(db, game_id) # Fetch game first
        if not game:
            raise GameNotFoundError(f"Game with ID {game_id} not found to expire.")
        if game.is_expired:
            # Optionally raise an error or just return the game if already expired
            # print(f"Game {game_id} is already expired.")
            return game

        updated_game = crud_games.expire_game_in_db(db, game_id)
        if not updated_game: # Should not happen if game was found initially
             raise DatabaseError(f"Failed to expire game {game_id} after finding it.")
        return updated_game


    def reactivate_game(self, db: Session, game_id: int) -> Game:
        game = crud_games.get_game_by_id(db, game_id) # Fetch game first
        if not game:
            raise GameNotFoundError(f"Game with ID {game_id} not found to reactivate.")
        if not game.is_expired:
            # Optionally raise an error or just return the game if already active
            # print(f"Game {game_id} is already active.")
            return game

        updated_game = crud_games.reactivate_game_in_db(db, game_id)
        if not updated_game:  # Should not happen
            raise DatabaseError(f"Failed to reactivate game {game_id} after finding it.")
        return updated_game


# -------- File Separator --------

# Filename: app/services/license_service.py
from sqlalchemy.orm import Session
from app.data import crud_license
from app.core.models import License
from app.core.exceptions import DatabaseError # Added DatabaseError


class LicenseService:
    def create_license_if_not_exists(self, db: Session, license_is_active: bool = False) -> License: # Renamed
        """Creates a license record if one doesn't already exist. Returns the existing or new license."""
        existing_license = crud_license.crud_get_license(db)
        if existing_license:
            return existing_license
        # crud_create_license in the original might return existing one,
        # but better to be explicit here.
        try:
            # If crud_create_license is changed to strictly create, this is fine.
            # If it can return existing, the check above is redundant.
            # Assuming crud_create_license will create if none exists.
            return crud_license.crud_create_license(db, license_is_active=license_is_active)
        except DatabaseError as e: # Catch if creation fails specifically
            # This might happen if crud_create_license fails due to a race condition
            # where another transaction created it. Try fetching again.
            existing_license = crud_license.crud_get_license(db)
            if existing_license:
                return existing_license
            raise e # Re-raise original DatabaseError if still not found

    def get_license(self, db: Session) -> License | None:
        """Retrieves the license record."""
        return crud_license.crud_get_license(db)

    def get_license_status(self, db: Session) -> bool:
        """Gets the current status of the license. Returns False if no license exists."""
        return crud_license.crud_get_license_status(db)

    def set_license_status(self, db: Session, license_activated: bool) -> License:
        """Sets the license status. Creates a license if none exists, then sets its status."""
        license_record = crud_license.crud_get_license(db)
        if not license_record:
            # Create it with the desired initial status directly.
            # crud_create_license might not take initial status correctly if it "returns existing".
            # This ensures if we create, it's with the intended status.
            license_record = self.create_license_if_not_exists(db, license_is_active=license_activated)
            # If it was just created, its status is already set.
            # If an existing one was returned by create_license_if_not_exists, we might need to update.
            # So, always ensure status is set after getting/creating.

        # Ensure the status is what's requested, even if it was just created or already existed.
        if license_record.is_active != license_activated:
            updated_license = crud_license.crud_set_license_status(db, license_activated)
            if not updated_license: # Should not happen if logic is correct
                raise DatabaseError("Failed to set license status after ensuring license exists.")
            return updated_license
        return license_record


# -------- File Separator --------

# Filename: app/services/user_service.py
from typing import Optional, List, Type
from sqlalchemy.orm import Session

from app.core.models import User # Explicit import of User model
from app.core.exceptions import UserNotFoundError, ValidationError, DatabaseError # Added DatabaseError
from app.data import crud_users
from app.constants import EMPLOYEE_ROLE, ALL_USER_ROLES # ALL_USER_ROLES for validation

class UserService:
    def get_user_by_id(self, db: Session, user_id: int) -> User: # Return User, raise if not found
        user = crud_users.get_user_by_id(db, user_id)
        if not user:
            raise UserNotFoundError(f"User with ID {user_id} not found.")
        return user

    def get_user_by_username(self, db: Session, username: str) -> User: # Return User, raise if not found
        user = crud_users.get_user_by_username(db, username)
        if not user:
            raise UserNotFoundError(f"User with username '{username}' not found.")
        return user

    def get_users_by_roles(self, db: Session, roles: List[str]) -> List[User]:
        # Validate roles if necessary
        for role in roles:
            if role not in ALL_USER_ROLES:
                raise ValidationError(f"Invalid role specified: {role}")
        return crud_users.get_users_by_roles(db, roles)

    def get_all_users(self, db: Session) -> List[User]:
        return crud_users.get_all_users(db)

    def any_users_exist(self, db: Session) -> bool: # Renamed from check_users_exist
        return crud_users.any_users_exist(db)

    def create_user(self, db: Session, username: str, password: str, role: str = EMPLOYEE_ROLE) -> User:
        if not username or not username.strip():
            raise ValidationError("Username cannot be empty.")
        if not password: # Add password complexity rules here if needed (e.g., length)
            raise ValidationError("Password cannot be empty.")
        if len(password) < 6: # Example rule
             raise ValidationError("Password must be at least 6 characters long.")
        if role not in ALL_USER_ROLES:
            raise ValidationError(f"Invalid user role: {role}.")
        # crud_users.create_user handles DatabaseError if username exists
        return crud_users.create_user(db, username.strip(), password, role)

    def update_user(self, db: Session, user_id: int, username: Optional[str] = None,
                    password: Optional[str] = None, role: Optional[str] = None, is_active: Optional[bool] = None) -> User:
        # Fetch user first to ensure it exists
        user_to_update = self.get_user_by_id(db, user_id) # This will raise UserNotFoundError if not found

        if username is not None and not username.strip():
            raise ValidationError("Username cannot be empty if provided for update.")
        if password is not None and not password: # If password is provided, it cannot be empty string
             raise ValidationError("New password cannot be empty.")
        if password is not None and len(password) < 6: # Example rule
             raise ValidationError("New password must be at least 6 characters long.")
        if role is not None and role not in ALL_USER_ROLES:
            raise ValidationError(f"Invalid user role for update: {role}.")

        # The CRUD operation will handle checking for username uniqueness if username is changed.
        return crud_users.update_user(db, user_id, username.strip() if username else None, password, role, is_active)

    def delete_user(self, db: Session, user_id: int) -> bool:
        # Ensure user exists before attempting delete
        user_to_delete = self.get_user_by_id(db, user_id) # Raises UserNotFoundError
        # Add any business logic checks here, e.g., cannot delete last admin user.
        return crud_users.delete_user(db, user_id)

    def deactivate_user(self, db: Session, user_id: int) -> User:
        user = self.get_user_by_id(db, user_id) # Ensures user exists
        if not user.is_active:
            # print(f"User {user_id} is already inactive.")
            return user # Or raise an error if trying to deactivate an already inactive user
        return crud_users.update_user(db, user_id, is_active=False)

    def reactivate_user(self, db: Session, user_id: int) -> User:
        user = self.get_user_by_id(db, user_id) # Ensures user exists
        if user.is_active:
            # print(f"User {user_id} is already active.")
            return user # Or raise an error
        return crud_users.update_user(db, user_id, is_active=True)


# -------- File Separator --------

# Filename: app/services/__init__.py
from .auth_service import AuthService
from .user_service import UserService
from .license_service import LicenseService
from .game_service import GameService # Added GameService

# -------- File Separator --------

# Filename: app/ui/router.py
import flet as ft

# Import Views (ensure these are correctly named and located)
from app.ui.views.login_view import LoginView
from app.ui.views.admin_dashboard_view import AdminDashboardView
from app.ui.views.employee_dashboard_view import EmployeeDashboardView
from app.ui.views.salesperson_dashboard_view import SalesPersonDashboardView
from app.ui.views.admin.game_management import GameManagementView
from app.ui.views.admin.book_management import BookManagementView

# Import constants for route names
from app.constants import (
    LOGIN_ROUTE, ADMIN_DASHBOARD_ROUTE, EMPLOYEE_DASHBOARD_ROUTE,
    SALESPERSON_DASHBOARD_ROUTE, GAME_MANAGEMENT_ROUTE, BOOK_MANAGEMENT_ROUTE
)

class Router:
    def __init__(self, page: ft.Page):
        self.page = page
        self.routes = {
            LOGIN_ROUTE: LoginView,
            ADMIN_DASHBOARD_ROUTE: AdminDashboardView,
            EMPLOYEE_DASHBOARD_ROUTE: EmployeeDashboardView,
            SALESPERSON_DASHBOARD_ROUTE: SalesPersonDashboardView,
            GAME_MANAGEMENT_ROUTE: GameManagementView,
            BOOK_MANAGEMENT_ROUTE: BookManagementView,
        }
        self.current_view_instance = None # Keep track of the current view instance
        self.current_route_name = None    # Keep track of current route name

    def navigate_to(self, route_name: str, **params):
        """
        Navigates to the specified route, clearing the page and instantiating the new view.
        """
        print(f"Navigating to '{route_name}' with params: {params}")

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
                print(f"Error instantiating view for route '{route_name}': {e}")
                # Fallback or error display logic
                self.page.controls.clear() # Clear potentially broken UI
                self.page.add(ft.Text(f"Error loading page: {route_name}. Details: {e}", color=ft.Colors.RED))
                # Optionally navigate to a known safe route like login
                if route_name != LOGIN_ROUTE:
                     self.navigate_to(LOGIN_ROUTE) # Avoid recursion if login itself fails
        else:
            print(f"Error: Route '{route_name}' not found. Navigating to login as fallback.")
            self.page.controls.clear()
            # Fallback to login view if route is unknown
            login_view_class = self.routes[LOGIN_ROUTE]
            self.current_view_instance = login_view_class(page=self.page, router=self) # No params for login usually
            self.page.add(self.current_view_instance)
            self.current_route_name = LOGIN_ROUTE

        self.page.update()


# -------- File Separator --------

# Filename: app/ui/__init__.py


# -------- File Separator --------

# Filename: app/ui/components/__init__.py


# -------- File Separator --------

# Filename: app/ui/components/forms/login_form.py
import flet as ft
from typing import Callable

from sqlalchemy.orm.exc import DetachedInstanceError # Keep for specific error handling

from app.services.auth_service import AuthService # Use AuthService
from app.data.database import get_db_session
from app.core.exceptions import AuthenticationError, ValidationError
from app.core.models import User

class LoginForm(ft.Container):
    def __init__(self, page: ft.Page, on_login_success: Callable[[User], None]):
        super().__init__() # Removed expand=True, let parent control expansion
        self.page = page
        self.on_login_success = on_login_success
        self.auth_service = AuthService()

        self.username_field = ft.TextField(
            label="Username",
            autofocus=True,
            expand=True,
            border_radius=8,
            prefix_icon=ft.Icons.PERSON_OUTLINE_ROUNDED,
            content_padding=ft.padding.symmetric(vertical=14, horizontal=12),
            on_submit=self._login_clicked_handler, # Ensure handler is method
        )
        self.password_field = ft.TextField(
            label="Password",
            password=True,
            can_reveal_password=True,
            expand=True,
            border_radius=8,
            prefix_icon=ft.Icons.LOCK_OUTLINE_ROUNDED,
            on_submit=self._login_clicked_handler, # Ensure handler is method
            content_padding=ft.padding.symmetric(vertical=14, horizontal=12)
        )
        self.error_text = ft.Text(
            visible=False,
            weight=ft.FontWeight.W_500,
            color=ft.Colors.RED_700,
            text_align=ft.TextAlign.CENTER # Center error text
        )
        self.login_button = ft.FilledButton(
            text="Login",
            expand=True, # Button expands
            height=48,
            on_click=self._login_clicked_handler, # Ensure handler is method
            icon=ft.Icons.LOGIN_ROUNDED,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)) # Consistent radius
        )
        self.content = self._build_layout()

    def _build_layout(self) -> ft.Column:
        return ft.Column(
            controls=[
                ft.Text(
                    "Welcome Back!",
                    style=ft.TextThemeStyle.HEADLINE_SMALL,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(
                    "Sign in to access your account.",
                    style=ft.TextThemeStyle.BODY_LARGE,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=20), # Spacing
                self.username_field,
                self.password_field,
                self.error_text,
                ft.Container(height=15), # Spacing
                self.login_button,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH, # Stretch fields/button
            spacing=12,
        )

    def _login_clicked_handler(self, e: Optional[ft.ControlEvent] = None): # Made method, accept event
        self.error_text.value = ""
        self.error_text.visible = False
        self.update() # Update to hide previous error immediately

        username = self.username_field.value.strip() if self.username_field.value else ""
        password = self.password_field.value if self.password_field.value else ""

        try:
            with get_db_session() as db:
                # Detach user_obj from session before passing to on_login_success if it causes issues
                user_obj = self.auth_service.authenticate_user(db, username, password)
                # db.expunge(user_obj) # Optional: if DetachedInstanceError is persistent
            self.on_login_success(user_obj)
        except (AuthenticationError, ValidationError) as ex:
            self.error_text.value = ex.message
            self.error_text.visible = True
        except DetachedInstanceError as di_err: # Specific SQLAlchemy error
            print(f"SQLAlchemy DetachedInstanceError during/after login success: {di_err}")
            self.error_text.value = "Login successful, but a session error occurred. Please retry."
            # Consider a more user-friendly message or specific recovery if possible.
            self.error_text.visible = True
        except Exception as ex_general: # Catch any other unexpected errors
            print(f"Unexpected error in login: {ex_general}")
            self.error_text.value = "An unexpected error occurred. Please try again."
            self.error_text.visible = True
        
        self.update() # Update to show new error or clear form elements if needed
        if self.page: self.page.update() # Update the page to reflect changes in the form

# -------- File Separator --------

# Filename: app/ui/components/forms/__init__.py


# -------- File Separator --------

# Filename: app/ui/components/tables/games_table.py
from math import ceil # Keep ceil for direct use if any overrides pagination
from typing import List, Callable, Optional, Type, Any, Dict
import flet as ft
import datetime

from app.core.exceptions import WidgetError, ValidationError, DatabaseError, GameNotFoundError
from app.core.models import Game
from app.services.game_service import GameService
from app.data.database import get_db_session # For db interactions within actions
from app.ui.components.common.paginated_data_table import PaginatedDataTable # Import base class
from app.ui.components.common.dialog_factory import create_confirmation_dialog # Import dialog factory

class GamesTable(PaginatedDataTable[Game]):
    def __init__(self, page: ft.Page, game_service: GameService,
                 on_data_changed_stats: Optional[Callable[[int, int, int], None]] = None): # Renamed for clarity

        self.game_service = game_service # Needs to be set before super().__init__ if used by its methods
        self._on_data_changed_stats = on_data_changed_stats
        self.current_action_game: Optional[Game] = None # For dialog context

        # Define column structure for the PaginatedDataTable base class
        column_definitions: List[Dict[str, Any]] = [
            {"key": "id", "label": "ID", "sortable": True, "numeric": False, "searchable": False,
             "display_formatter": lambda val: ft.Text(str(val), size=12.5)},
            {"key": "name", "label": "Game Name", "sortable": True, "numeric": False, "searchable": True,
             "display_formatter": lambda val: ft.Text(str(val), size=12.5, weight=ft.FontWeight.W_500)},
            {"key": "game_number", "label": "Game No.", "sortable": True, "numeric": True, "searchable": True,
             "display_formatter": lambda val: ft.Text(str(val), size=12.5)},
            {"key": "price", "label": "Price ($)", "sortable": True, "numeric": True, "searchable": True,
             "display_formatter": lambda val_cents: ft.Text(f"{val_cents/100:.2f}", size=12.5),
             "custom_sort_value_getter": lambda game: game.price}, # Sort by cents
            {"key": "total_tickets", "label": "Tickets", "sortable": True, "numeric": True, "searchable": True,
             "display_formatter": lambda val: ft.Text(str(val), size=12.5)},
            {"key": "calculated_total_value", "label": "Value ($)", "sortable": True, "numeric": True, "searchable": True,
             "display_formatter": lambda val_cents, item: ft.Text(f"{item.calculated_total_value/100:.2f}", size=12.5),
             "custom_sort_value_getter": lambda game: game.calculated_total_value},
            {"key": "default_ticket_order", "label": "Order", "sortable": True, "numeric": False, "searchable": False,
             "display_formatter": lambda val: ft.Text(str(val).capitalize(), size=12.5)},
            {"key": "created_date", "label": "Created", "sortable": True, "numeric": False, "searchable": False,
             "display_formatter": lambda val_date: ft.Text(val_date.strftime("%Y-%m-%d") if val_date else "", size=12.5)},
            {"key": "expired_date", "label": "Expired", "sortable": True, "numeric": False, "searchable": False,
             "display_formatter": self._format_expired_date_cell}, # Use a method for complex formatting
        ]

        super().__init__(
            page=page,
            fetch_all_data_func=self._fetch_games_data,
            column_definitions=column_definitions,
            action_cell_builder=self._build_action_cell,
            rows_per_page=10, # Default, can be changed
            initial_sort_key="id", # Default sort, e.g., by ID or game_number
            initial_sort_ascending=True,
            # on_data_stats_changed will be handled by overriding _filter_and_sort_displayed_data
            # or by calling the stats update explicitly after data refresh.
        )
        # self.refresh_data_and_ui() # Initial data load should be triggered by the view containing this table

    def _fetch_games_data(self, db_session) -> List[Game]:
        """Implements data fetching for games."""
        return self.game_service.get_all_games(db_session)

    def _format_expired_date_cell(self, expired_date_val: Optional[datetime.datetime], item: Game) -> ft.Control:
        """ Custom formatter for the 'Expired' date cell to show 'Active' status. """
        if item.is_expired and expired_date_val:
            return ft.Text(expired_date_val.strftime("%Y-%m-%d"), size=12.5, color=ft.Colors.RED_ACCENT_700)
        elif not item.is_expired:
            return ft.Text("Active", color=ft.Colors.GREEN_700, weight=ft.FontWeight.BOLD, size=12.5)
        return ft.Text("", size=12.5) # Should not happen if logic is correct (is_expired implies date or vice-versa)

    def _build_action_cell(self, game: Game, table_instance: PaginatedDataTable) -> ft.DataCell:
        """Builds the DataCell containing action buttons for a game."""
        actions_controls = []
        edit_button = ft.IconButton(
            ft.Icons.EDIT_ROUNDED, tooltip="Edit Game", icon_color=ft.Colors.PRIMARY,
            icon_size=18, on_click=lambda e, g=game: self._open_edit_game_dialog(g))
        actions_controls.append(edit_button)

        if not game.is_expired:
            expire_button = ft.IconButton(
                ft.Icons.REMOVE_CIRCLE_OUTLINE_ROUNDED, tooltip="Expire game", icon_color=ft.Colors.RED_ACCENT_700,
                icon_size=18, on_click=lambda e, g=game: self._confirm_expire_game_dialog(g))
            actions_controls.append(expire_button)
        else:
            reactivate_button = ft.IconButton(
                ft.Icons.ADD_CIRCLE_OUTLINE_ROUNDED, tooltip="Reactivate Game", icon_color=ft.Colors.GREEN_ACCENT_700,
                icon_size=18, on_click=lambda e, g=game: self._confirm_reactivate_game_dialog(g))
            actions_controls.append(reactivate_button)

        return ft.DataCell(ft.Row(actions_controls, spacing=-5, alignment=ft.MainAxisAlignment.END, vertical_alignment=ft.CrossAxisAlignment.CENTER))

    # Override to update specific stats after data is filtered/sorted
    def _filter_and_sort_displayed_data(self, search_term: str = ""):
        super()._filter_and_sort_displayed_data(search_term) # Call base class method
        if self._on_data_changed_stats and self._all_unfiltered_data is not None:
            # Calculate stats based on the *unfiltered* data
            total_games = len(self._all_unfiltered_data)
            active_games = sum(1 for g in self._all_unfiltered_data if not g.is_expired)
            expired_games = sum(1 for g in self._all_unfiltered_data if g.is_expired)
            self._on_data_changed_stats(total_games, active_games, expired_games)

    def _open_edit_game_dialog(self, game: Game):
        # This was a placeholder, remains so.
        self.page.open(ft.SnackBar(ft.Text(f"Edit game {game.name} - (Not Implemented)"), open=True))


    def _confirm_expire_game_dialog(self, game: Game):
        self.current_action_game = game
        dialog_content = ft.Text(f"Are you sure you want to expire game '{game.name}' (Number: {game.game_number})? Make sure all book instances' sales are recorded.")
        
        confirm_dialog = create_confirmation_dialog(
            title_text="Confirm Expire",
            title_color=ft.Colors.RED_700,
            content_control=dialog_content,
            on_confirm=self._handle_expire_confirmed,
            on_cancel=lambda e: self.close_dialog_and_refresh(self.page.dialog), # type: ignore
            confirm_button_text="Expire Game",
            confirm_button_style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE)
        )
        self.page.dialog = confirm_dialog
        self.page.open(self.page.dialog)

    def _handle_expire_confirmed(self, e=None):
        if not self.current_action_game: return
        game_to_expire = self.current_action_game
        current_dialog = self.page.dialog # Store current dialog instance

        try:
            with get_db_session() as db:
                self.game_service.expire_game(db, game_id=game_to_expire.id) # type: ignore
            self.close_dialog_and_refresh(current_dialog, f"Game '{game_to_expire.name}' expired.")
        except GameNotFoundError as ex:
            self.show_error_snackbar(str(ex))
            self.close_dialog_and_refresh(current_dialog) # Still close dialog and refresh list
        except DatabaseError as ex:
            self.show_error_snackbar(f"Database error expiring game: {ex.message}")
            self.close_dialog_and_refresh(current_dialog)
        except Exception as ex_general:
            self.show_error_snackbar(f"An unexpected error occurred: {ex_general}")
            self.close_dialog_and_refresh(current_dialog)
        finally:
            self.current_action_game = None


    def _confirm_reactivate_game_dialog(self, game: Game):
        self.current_action_game = game
        dialog_content = ft.Text(f"Are you sure you want to re-activate game '{game.name}' (Number: {game.game_number})? Associated books may need separate reactivation.")
        
        confirm_dialog = create_confirmation_dialog(
            title_text="Confirm Reactivate",
            title_color=ft.Colors.GREEN_700,
            content_control=dialog_content,
            on_confirm=self._handle_reactivate_confirmed,
            on_cancel=lambda e: self.close_dialog_and_refresh(self.page.dialog), # type: ignore
            confirm_button_text="Reactivate Game",
            confirm_button_style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)
        )
        self.page.dialog = confirm_dialog
        self.page.open(self.page.dialog)

    def _handle_reactivate_confirmed(self, e=None):
        if not self.current_action_game: return
        game_to_reactivate = self.current_action_game
        current_dialog = self.page.dialog

        try:
            with get_db_session() as db:
                self.game_service.reactivate_game(db, game_id=game_to_reactivate.id) # type: ignore
            self.close_dialog_and_refresh(current_dialog, f"Game '{game_to_reactivate.name}' reactivated.")
        except GameNotFoundError as ex:
            self.show_error_snackbar(str(ex))
            self.close_dialog_and_refresh(current_dialog)
        except DatabaseError as ex:
            self.show_error_snackbar(f"Database error reactivating game: {ex.message}")
            self.close_dialog_and_refresh(current_dialog)
        except Exception as ex_general:
            self.show_error_snackbar(f"An unexpected error occurred: {ex_general}")
            self.close_dialog_and_refresh(current_dialog)
        finally:
            self.current_action_game = None

# -------- File Separator --------

# Filename: app/ui/components/tables/users_table.py
from typing import List, Callable, Optional, Type, Dict, Any
import flet as ft
import datetime

from app.constants import ADMIN_ROLE, EMPLOYEE_ROLE, SALESPERSON_ROLE, MANAGED_USER_ROLES
from app.core.exceptions import WidgetError, ValidationError, DatabaseError, UserNotFoundError
from app.core.models import User
from app.services.user_service import UserService
from app.data.database import get_db_session
from app.ui.components.common.paginated_data_table import PaginatedDataTable # Import base class
from app.ui.components.common.dialog_factory import create_confirmation_dialog, create_form_dialog # Import dialog factory

class UsersTable(PaginatedDataTable[User]):
    def __init__(self, page: ft.Page, user_service: UserService,
                 initial_roles_to_display: List[str], # Used for initial data fetch query
                 on_data_changed_callback: Optional[Callable[[], None]] = None): # Renamed for clarity

        self.user_service = user_service
        self.initial_roles_to_display = initial_roles_to_display
        if not self.initial_roles_to_display:
            raise WidgetError("User roles must be provided for UsersTable.")
        self._on_data_changed_callback = on_data_changed_callback
        self.current_action_user: Optional[User] = None # For dialog context

        column_definitions: List[Dict[str, Any]] = [
            {"key": "id", "label": "ID", "sortable": True, "numeric": False, "searchable": False,
             "display_formatter": lambda val: ft.Text(str(val))},
            {"key": "username", "label": "Username", "sortable": True, "numeric": False, "searchable": True,
             "display_formatter": lambda val: ft.Text(str(val))},
            {"key": "role", "label": "Role", "sortable": True, "numeric": False, "searchable": True, # Role can be searched
             "display_formatter": lambda val: ft.Text(str(val).capitalize())},
            {"key": "created_date", "label": "Created Date", "sortable": True, "numeric": False, "searchable": False,
             "display_formatter": lambda val_date: ft.Text(val_date.strftime("%Y-%m-%d %H:%M") if val_date else "")},
            {"key": "is_active", "label": "Is Active?", "sortable": True, "numeric": False, "searchable": False, # Not directly searchable as bool
             "display_formatter": lambda val_bool: ft.Text("Yes" if val_bool else "No", color=ft.Colors.GREEN if val_bool else ft.Colors.RED)},
        ]

        super().__init__(
            page=page,
            fetch_all_data_func=self._fetch_users_data,
            column_definitions=column_definitions,
            action_cell_builder=self._build_action_cell,
            rows_per_page=10, # Users table might show more, adjust as needed
            initial_sort_key="username",
            initial_sort_ascending=True,
            show_pagination=False, # UsersTable did not have pagination, keeping that look
            default_search_enabled=False, # UsersTable did not have search, keeping that look
        )
        # self.refresh_data_and_ui() # Initial load triggered by view

    def _fetch_users_data(self, db_session) -> List[User]:
        """Implements data fetching for users based on initial roles."""
        # If self.initial_roles_to_display is empty or ALL, fetch all users
        if not self.initial_roles_to_display or set(self.initial_roles_to_display) == set(ALL_USER_ROLES):
             return self.user_service.get_all_users(db_session)
        return self.user_service.get_users_by_roles(db_session, roles=self.initial_roles_to_display)

    def _build_action_cell(self, user: User, table_instance: PaginatedDataTable) -> ft.DataCell:
        actions_controls = []
        edit_button = ft.IconButton(
            icon=ft.Icons.EDIT_ROUNDED, tooltip="Edit user", icon_color=ft.Colors.PRIMARY,
            on_click=lambda e, u=user: self._open_edit_user_dialog(u)
        )
        actions_controls.append(edit_button)

        if user.role != SALESPERSON_ROLE: # Salespersons cannot be deactivated via this generic table interface
            if user.is_active:
                deactivate_button = ft.IconButton(
                    icon=ft.Icons.DESKTOP_ACCESS_DISABLED_OUTLINED, tooltip="Deactivate user", icon_color=ft.Colors.RED_ACCENT_700,
                    on_click=lambda e, u=user: self._confirm_deactivate_user_dialog(u)
                )
                actions_controls.append(deactivate_button)
            else:
                reactivate_button = ft.IconButton(
                    icon=ft.Icons.DESKTOP_WINDOWS_ROUNDED, tooltip="Reactivate user", icon_color=ft.Colors.GREEN_ACCENT_700,
                    on_click=lambda e, u=user: self._confirm_reactivate_user_dialog(u)
                )
                actions_controls.append(reactivate_button)
        
        return ft.DataCell(ft.Row(actions_controls, spacing=0, alignment=ft.MainAxisAlignment.END))

    def _filter_and_sort_displayed_data(self, search_term: str = ""):
        super()._filter_and_sort_displayed_data(search_term)
        if self._on_data_changed_callback:
            self._on_data_changed_callback()

    # --- Dialog handling specific to UsersTable ---
    def _close_dialog_and_refresh_users(self, dialog_to_close: Optional[ft.AlertDialog]=None, success_message: Optional[str]=None):
        if dialog_to_close and self.page.dialog == dialog_to_close:
            self.page.close(dialog_to_close)
        if success_message and self.page:
            self.page.open(ft.SnackBar(ft.Text(success_message), open=True))
        self.refresh_data_and_ui() # Refresh user data

    # --- Edit User Dialog (Complex Form Dialog - kept mostly as is but uses factory for shell) ---
    def _open_edit_user_dialog(self, user: User):
        self.current_action_user = user

        # Form fields
        username_field = ft.TextField(label="Username", value=user.username, disabled=True) # Username typically not editable
        role_options = [ft.dropdown.Option(role, role.capitalize()) for role in MANAGED_USER_ROLES]
        role_dropdown = ft.Dropdown(
            label="Role", options=role_options, value=user.role,
            disabled=(user.role == SALESPERSON_ROLE) # Salesperson role cannot be changed
        )
        password_field = ft.TextField(label="New Password (optional)", password=True, can_reveal_password=True)
        confirm_password_field = ft.TextField(label="Confirm New Password", password=True, can_reveal_password=True)
        error_text_edit = ft.Text(visible=False, color=ft.Colors.RED_700)

        form_column = ft.Column(
            [
                username_field, role_dropdown,
                ft.Text("Leave password fields blank to keep current password.", italic=True, size=12),
                password_field, confirm_password_field, error_text_edit,
            ],
            tight=True, spacing=15, width=350, height=350, scroll=ft.ScrollMode.AUTO
        )

        # Save handler needs access to these fields
        def _save_edits_handler(e):
            self._save_user_edits(role_dropdown, password_field, confirm_password_field, error_text_edit)

        edit_dialog = create_form_dialog(
            page=self.page,
            title_text=f"Edit User: {user.username}",
            form_content_column=form_column,
            on_save_callback=_save_edits_handler,
            on_cancel_callback=lambda ev: self._close_dialog_and_refresh_users(self.page.dialog) # type: ignore
        )
        self.page.dialog = edit_dialog
        self.page.open(self.page.dialog)


    def _save_user_edits(self, role_field: ft.Dropdown, password_field: ft.TextField,
                         confirm_password_field: ft.TextField, error_text_edit: ft.Text):
        if not self.current_action_user: return

        error_text_edit.value = ""
        error_text_edit.visible = False
        # error_text_edit.update() # Handled by page update

        new_role = role_field.value
        new_password = password_field.value if password_field.value else None # Ensure None if empty
        confirm_new_password = confirm_password_field.value

        try:
            # Password validation
            if new_password:
                if len(new_password) < 6:
                    raise ValidationError("New password must be at least 6 characters.")
                if new_password != confirm_new_password:
                    raise ValidationError("New passwords do not match.")
            
            with get_db_session() as db:
                self.user_service.update_user(
                    db, user_id=self.current_action_user.id, # type: ignore
                    password=new_password, role=new_role
                )
            self._close_dialog_and_refresh_users(self.page.dialog, "User details updated successfully.") # type: ignore
        except (ValidationError, DatabaseError, UserNotFoundError) as ex:
            error_text_edit.value = str(ex)
            error_text_edit.visible = True
        except Exception as ex_general:
            error_text_edit.value = f"An unexpected error occurred: {ex_general}"
            error_text_edit.visible = True
        
        if self.page: self.page.update() # Update dialog with error or after closing


    # --- Confirmation Dialogs (Deactivate/Reactivate - use DialogFactory) ---
    def _confirm_deactivate_user_dialog(self, user: User):
        self.current_action_user = user
        content = ft.Text(f"Are you sure you want to deactivate user '{user.username}' (ID: {user.id})?")
        dialog = create_confirmation_dialog(
            title_text="Confirm Deactivate", title_color=ft.Colors.RED_700, content_control=content,
            on_confirm=self._handle_deactivate_confirmed,
            on_cancel=lambda e: self._close_dialog_and_refresh_users(self.page.dialog), # type: ignore
            confirm_button_text="Deactivate User",
            confirm_button_style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE)
        )
        self.page.dialog = dialog
        self.page.open(self.page.dialog)

    def _handle_deactivate_confirmed(self, e=None):
        if not self.current_action_user: return
        user_to_deactivate = self.current_action_user
        current_dialog = self.page.dialog
        try:
            with get_db_session() as db:
                self.user_service.deactivate_user(db, user_id=user_to_deactivate.id) # type: ignore
            self._close_dialog_and_refresh_users(current_dialog, f"User '{user_to_deactivate.username}' deactivated.")
        except (UserNotFoundError, DatabaseError) as ex:
            self.show_error_snackbar(str(ex)) # Use base class snackbar
            self._close_dialog_and_refresh_users(current_dialog)
        except Exception as ex_general:
            self.show_error_snackbar(f"An unexpected error: {ex_general}")
            self._close_dialog_and_refresh_users(current_dialog)
        finally: self.current_action_user = None


    def _confirm_reactivate_user_dialog(self, user: User):
        self.current_action_user = user
        content = ft.Text(f"Are you sure you want to reactivate user '{user.username}' (ID: {user.id})?")
        dialog = create_confirmation_dialog(
            title_text="Confirm Reactivate", title_color=ft.Colors.GREEN_700, content_control=content,
            on_confirm=self._handle_reactivate_confirmed,
            on_cancel=lambda e: self._close_dialog_and_refresh_users(self.page.dialog), # type: ignore
            confirm_button_text="Reactivate User",
            confirm_button_style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)
        )
        self.page.dialog = dialog
        self.page.open(self.page.dialog)

    def _handle_reactivate_confirmed(self, e=None):
        if not self.current_action_user: return
        user_to_reactivate = self.current_action_user
        current_dialog = self.page.dialog
        try:
            with get_db_session() as db:
                self.user_service.reactivate_user(db, user_id=user_to_reactivate.id) # type: ignore
            self._close_dialog_and_refresh_users(current_dialog, f"User '{user_to_reactivate.username}' reactivated.")
        except (UserNotFoundError, DatabaseError) as ex:
            self.show_error_snackbar(str(ex))
            self._close_dialog_and_refresh_users(current_dialog)
        except Exception as ex_general:
            self.show_error_snackbar(f"An unexpected error: {ex_general}")
            self._close_dialog_and_refresh_users(current_dialog)
        finally: self.current_action_user = None

# -------- File Separator --------

# Filename: app/ui/components/tables/__init__.py


# -------- File Separator --------

# Filename: app/ui/components/widgets/function_button.py
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
        height: float = 150, # Consider making this adaptable or passed in
        width: float = 150,  # Consider making this adaptable or passed in
) -> ft.Card:

    effective_router_params = router_params if router_params is not None else {}

    def handle_click(e): # Renamed event arg to 'e' for convention
        if disabled:
            return
        # print(f"NavCard Clicked: Navigating to {navigate_to_route} with params {effective_router_params}")
        if hasattr(router, 'navigate_to'): # For your custom Router class
            router.navigate_to(navigate_to_route, **effective_router_params)
        elif hasattr(router, 'go'): # For Flet's page.go
             router.go(navigate_to_route) # Flet's page.go doesn't take arbitrary params directly
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
        border_radius=ft.border_radius.all(border_radius), # Use ft.border_radius
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
        # surface_tint_color might be useful with Material 3 theming
    )

# -------- File Separator --------

# Filename: app/ui/components/widgets/number_decimal_input.py
import flet as ft
from typing import Optional # Added Optional for type hinting

class NumberDecimalField(ft.TextField):
    def __init__(self,
                 label: str = "Enter number",
                 hint_text: Optional[str] = None,  # Allow None
                 is_money_field: bool = False,
                 currency_symbol: str = "$",
                 is_integer_only: bool = False,
                 **kwargs):

        self.is_integer_only = is_integer_only
        self.is_money_field = is_money_field
        self.currency_symbol = currency_symbol # Store for potential use
        self.last_valid_value = "" # Stores the last known good value

        current_regex_string = r"[0-9]" if self.is_integer_only else r"[0-9.]"

        if hint_text is None:
            if self.is_integer_only:
                default_hint = "e.g., 123"
            elif self.is_money_field:
                # For money, hint usually includes symbol and decimal format
                default_hint = f"e.g., {self.currency_symbol}10.50" if not self.is_integer_only else f"e.g., {self.currency_symbol}10"
            else: # Generic decimal
                default_hint = "e.g., 10.99 or 10"
        else:
            default_hint = hint_text

        prefix_widget = None
        if self.is_money_field: # Show currency symbol for money fields (int or decimal)
             prefix_widget = ft.Text(self.currency_symbol, weight=ft.FontWeight.BOLD, size=16, text_align=ft.TextAlign.CENTER)


        super().__init__(
            label=label,
            hint_text=default_hint,
            input_filter=ft.InputFilter(
                allow=True, # Allow based on regex
                regex_string=current_regex_string,
                replacement_string="" # Discard non-matching characters
            ),
            keyboard_type=ft.KeyboardType.NUMBER, # Suggests numeric keyboard
            on_change=self._validate_input_on_change, # Changed to more descriptive name
            prefix=prefix_widget, # Use prefix for currency symbol
            **kwargs
        )

    def _is_valid_current_format(self, value: str) -> bool:
        """Checks if the current string value is a valid number format based on field type."""
        if not value: # Empty is valid during typing
            return True
        if self.is_integer_only:
            return value.isdigit()
        # Decimal or money (which is also decimal unless specified as integer only, handled above)
        if value.count('.') > 1:
            return False
        if value == ".": # A single dot is not a valid number
            return False
        try:
            float(value) # Check if convertible to float
            return True
        except ValueError:
            return False

    def _validate_input_on_change(self, e: ft.ControlEvent):
        """Validates the input on each change event."""
        current_value = e.control.value

        # Filter for integer-only fields (e.g., if user pastes a decimal)
        if self.is_integer_only and '.' in current_value:
            e.control.value = self.last_valid_value # Revert to last valid
            e.control.error_text = "Only whole numbers allowed."
            e.control.update()
            return

        if self._is_valid_current_format(current_value):
            # For money fields (non-integer), check decimal places
            if self.is_money_field and not self.is_integer_only and '.' in current_value:
                parts = current_value.split('.')
                if len(parts) > 1 and len(parts[1]) > 2: # Max 2 decimal places
                    e.control.value = self.last_valid_value # Revert
                    e.control.error_text = "Max 2 decimal places for money."
                    e.control.update()
                    return

            self.last_valid_value = current_value # Update last valid value
            if e.control.error_text: # Clear error if input becomes valid
                e.control.error_text = None
                e.control.update()
        else:
            # Revert to last valid value if current input is invalid
            e.control.value = self.last_valid_value
            e.control.error_text = "Invalid number format." # Generic error
            e.control.update()

    def get_value_as_int(self) -> Optional[int]:
        """Returns the current value as an integer, or None if invalid or not an integer."""
        if self.value and self._is_valid_current_format(self.value):
            try:
                if self.is_integer_only:
                    return int(self.value)
                # For decimal fields, return int if it's a whole number
                f_val = float(self.value)
                if f_val == int(f_val):
                    return int(f_val)
            except ValueError:
                return None # Should ideally be caught by _is_valid_current_format
        return None

    def get_value_as_float(self) -> Optional[float]:
        """Returns the current value as a float, or None if invalid."""
        if self.value and self._is_valid_current_format(self.value):
            try:
                # Ensure money format (2 decimal places) isn't violated on final get
                if self.is_money_field and not self.is_integer_only and '.' in self.value:
                    parts = self.value.split('.')
                    if len(parts) > 1 and len(parts[1]) > 2:
                         # This state should ideally be prevented by on_change, but as a safeguard
                        return None
                return float(self.value)
            except ValueError:
                return None
        return None

    def get_value_as_str(self) -> str:
        """Returns the raw string value."""
        return self.value if self.value else ""

    def clear(self):
        """Clears the input field."""
        self.value = ""
        self.last_valid_value = ""
        self.error_text = None
        self.update()

# -------- File Separator --------

# Filename: app/ui/components/widgets/__init__.py
from .function_button import create_nav_card_button
from .number_decimal_input import NumberDecimalField

# -------- File Separator --------

# Filename: app/ui/views/admin_dashboard_view.py
import flet as ft
from app.constants import LOGIN_ROUTE, GAME_MANAGEMENT_ROUTE, ADMIN_DASHBOARD_ROUTE, BOOK_MANAGEMENT_ROUTE
from app.core.models import User
from app.ui.components.widgets.function_button import create_nav_card_button
from app.ui.components.common.appbar_factory import create_appbar # Import AppBar factory

class AdminDashboardView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user: User, license_status: bool, **params):
        super().__init__(expand=True)
        self.page = page
        self.router = router
        self.current_user = current_user
        self.license_status = license_status

        # Navigation parameters for child views, allowing them to return here
        self.navigation_params_for_children = {
            "current_user": self.current_user,
            "license_status": self.license_status,
            "previous_view_route": ADMIN_DASHBOARD_ROUTE, # This view's route
            "previous_view_params": { # Params needed to reconstruct this view if returned to
                "current_user": self.current_user,
                "license_status": self.license_status,
            },
        }

        self.page.appbar = create_appbar(
            page=self.page,
            router=self.router,
            title_text="Admin Dashboard",
            current_user=self.current_user,
            license_status=self.license_status
        )
        self.content = self._build_body()

    def _create_section_quadrant(self, title: str, title_color: str,
                                 button_row_controls: list, gradient_colors: list) -> ft.Container:
        """Helper to create a styled, scrollable container for a function section (quadrant)."""
        scrollable_content = ft.Column(
            controls=[
                ft.Text(
                    title,
                    weight=ft.FontWeight.BOLD,
                    size=20,
                    color=title_color,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Row(
                    controls=button_row_controls,
                    spacing=10,
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    wrap=True, # Allow buttons to wrap if quadrant is too narrow
                ),
            ],
            spacing=15,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.ADAPTIVE, # Enable scrolling for content overflow
            # Do not set expand=True here for scrollable_content
        )

        quadrant_container = ft.Container(
            content=scrollable_content,
            padding=15,
            border_radius=ft.border_radius.all(10),
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=gradient_colors,
            ),
            expand=True, # Quadrant container expands to fill its grid cell
            alignment=ft.alignment.center, # Center the scrollable content within
        )
        return quadrant_container

    def _build_sales_functions_quadrant(self) -> ft.Container:
        buttons = [
            create_nav_card_button(
                router=self.router, text="Sales Entry", icon_name=ft.Icons.POINT_OF_SALE_ROUNDED,
                accent_color=ft.Colors.GREEN_700, navigate_to_route=LOGIN_ROUTE, tooltip="Add Daily Sales", disabled=True), # Example disabled
            create_nav_card_button(
                router=self.router, text="Book Sale", icon_name=ft.Icons.BOOK_ONLINE_ROUNDED,
                accent_color=ft.Colors.BLUE_700, navigate_to_route=LOGIN_ROUTE, tooltip="Add Book Sale", disabled=True),
            create_nav_card_button(
                router=self.router, text="Open Book", icon_name=ft.Icons.AUTO_STORIES_ROUNDED,
                accent_color=ft.Colors.TEAL_700, navigate_to_route=LOGIN_ROUTE, tooltip="Open Book", disabled=True),
        ]
        return self._create_section_quadrant(
            title="Sale Functions", title_color=ft.Colors.CYAN_900,
            button_row_controls=buttons,
            gradient_colors=[ft.Colors.CYAN_50, ft.Colors.LIGHT_BLUE_100]
        )

    def _build_inventory_functions_quadrant(self) -> ft.Container:
        buttons = [
            create_nav_card_button(
                router=self.router, text="Manage Games", icon_name=ft.Icons.SPORTS_ESPORTS_ROUNDED,
                accent_color=ft.Colors.DEEP_PURPLE_600, navigate_to_route=GAME_MANAGEMENT_ROUTE,
                tooltip="View, edit, or add game types", router_params=self.navigation_params_for_children,
            ),
            create_nav_card_button(
                router=self.router, text="Manage Books", icon_name=ft.Icons.MENU_BOOK_ROUNDED,
                accent_color=ft.Colors.BROWN_600, navigate_to_route=BOOK_MANAGEMENT_ROUTE, # Placeholder, assuming BOOK_MANAGEMENT_ROUTE
                tooltip="View, edit, or add lottery ticket books", router_params=self.navigation_params_for_children,
            ),
        ]
        return self._create_section_quadrant(
            title="Inventory Control", title_color=ft.Colors.GREEN_800,
            button_row_controls=buttons,
            gradient_colors=[ft.Colors.GREEN_100, ft.Colors.LIGHT_GREEN_200]
        )

    def _build_report_functions_quadrant(self) -> ft.Container:
        buttons = [
            create_nav_card_button(
                router=self.router, text="Sales by Date", icon_name=ft.Icons.CALENDAR_MONTH_ROUNDED,
                accent_color=ft.Colors.ORANGE_700, navigate_to_route=LOGIN_ROUTE, tooltip="Sales Report", disabled=True),
            create_nav_card_button(
                router=self.router, text="Book Open Report", icon_name=ft.Icons.ASSESSMENT_ROUNDED,
                accent_color=ft.Colors.INDIGO_400, navigate_to_route=LOGIN_ROUTE, tooltip="Book Open Report", disabled=True),
            create_nav_card_button(
                router=self.router, text="Game Expiry Report", icon_name=ft.Icons.UPDATE_ROUNDED,
                accent_color=ft.Colors.DEEP_ORANGE_700, navigate_to_route=LOGIN_ROUTE, tooltip="Game Expire Report", disabled=True),
            create_nav_card_button(
                router=self.router, text="Stock Levels", icon_name=ft.Icons.STACKED_BAR_CHART_ROUNDED,
                accent_color=ft.Colors.BROWN_500, navigate_to_route=LOGIN_ROUTE, tooltip="Book Stock Report", disabled=True),
        ]
        return self._create_section_quadrant(
            title="Data & Reports", title_color=ft.Colors.AMBER_900,
            button_row_controls=buttons,
            gradient_colors=[ft.Colors.AMBER_50, ft.Colors.YELLOW_100]
        )

    def _build_management_functions_quadrant(self) -> ft.Container:
        buttons = [
            create_nav_card_button(
                router=self.router, text="Manage Users", icon_name=ft.Icons.MANAGE_ACCOUNTS_ROUNDED,
                accent_color=ft.Colors.INDIGO_700, navigate_to_route=LOGIN_ROUTE, tooltip="Manage Users", disabled=True), # Assuming a route for user management
            create_nav_card_button(
                router=self.router, text="Backup Database", icon_name=ft.Icons.SETTINGS_BACKUP_RESTORE_ROUNDED,
                accent_color=ft.Colors.BLUE_800, navigate_to_route=LOGIN_ROUTE, tooltip="Backup Database", disabled=True),
        ]
        return self._create_section_quadrant(
            title="System Management", title_color=ft.Colors.DEEP_PURPLE_800,
            button_row_controls=buttons,
            gradient_colors=[ft.Colors.DEEP_PURPLE_50, ft.Colors.INDIGO_100]
        )

    def _build_body(self) -> ft.Column:
        divider_color = ft.Colors.with_opacity(0.3, ft.Colors.ON_SURFACE)
        divider_thickness = 2

        # Create a responsive grid for the quadrants
        # On larger screens, it could be 2x2. On smaller, 1xN.
        # For simplicity with Flet's Row/Column, we'll keep 2x2 for now.
        # Flet's ResponsiveRow could be used for more complex responsive layouts.

        main_content_area = ft.GridView(
            runs_count=2, # Try to fit 2 items per row (effectively 2 columns if items are wide enough)
            max_extent=self.page.width / 2.2 if self.page.width else 400, # Max width of each child
            child_aspect_ratio=1.0, # Adjust for desired height relative to width
            spacing=10,
            run_spacing=10,
            expand=True, # GridView expands
            controls=[ # Quadrants will try to fit based on max_extent
                self._build_sales_functions_quadrant(),
                self._build_inventory_functions_quadrant(),
                self._build_report_functions_quadrant(),
                self._build_management_functions_quadrant(),
            ],
        )
        # Fallback to Column layout if GridView doesn't provide desired control or for simplicity:
        row1 = ft.Row(
            controls=[
                self._build_sales_functions_quadrant(),
                # ft.VerticalDivider(width=divider_thickness, thickness=divider_thickness, color=divider_color),
                self._build_inventory_functions_quadrant(),
            ],
            spacing=10, expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH
        )
        row2 = ft.Row(
            controls=[
                self._build_report_functions_quadrant(),
                # ft.VerticalDivider(width=divider_thickness, thickness=divider_thickness, color=divider_color),
                self._build_management_functions_quadrant(),
            ],
            spacing=10, expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH
        )

        return ft.Column(
            controls=[row1, ft.Divider(height=divider_thickness, thickness=divider_thickness, color=divider_color), row2],
            spacing=10, expand=True,
        )

    # Logout method is handled by the appbar_factory's logout button
    # def logout(self, e):
    #     self.current_user = None
    #     self.router.navigate_to(LOGIN_ROUTE)


# -------- File Separator --------

# Filename: app/ui/views/employee_dashboard_view.py
import flet as ft
from app.constants import LOGIN_ROUTE
from app.core.models import User
from app.ui.components.common.appbar_factory import create_appbar # Import AppBar factory

class EmployeeDashboardView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user: User, license_status: bool, **params):
        super().__init__(expand=True)
        self.page = page
        self.router = router
        self.current_user = current_user
        self.license_status = license_status

        self.page.appbar = create_appbar(
            page=self.page,
            router=self.router,
            title_text="Employee Dashboard",
            current_user=self.current_user, # Show current user
            license_status=self.license_status,
            show_user_info=True # Explicitly show user info
        )
        self.content = self._build_body()

    def _build_body(self) -> ft.Container:
        welcome_message = "Welcome, Employee!"
        if self.current_user and self.current_user.username:
            welcome_message = f"Welcome, {self.current_user.username}!"

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(welcome_message, size=28, weight=ft.FontWeight.BOLD),
                    ft.Text("This is the Employee Dashboard. Functionality to be added.", size=16),
                    # Add employee-specific functions/buttons here
                    # e.g., ft.FilledButton("Enter Daily Sales", on_click=lambda e: print("Sales Entry Clicked"))
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=20,
            ),
            padding=50,
            alignment=ft.alignment.center,
            expand=True
        )

    # Logout method is handled by the appbar_factory's logout button
    # def logout(self, e):
    #     self.current_user = None
    #     self.router.navigate_to(LOGIN_ROUTE)


# -------- File Separator --------

# Filename: app/ui/views/login_view.py
import flet as ft

from app.services.auth_service import AuthService
from app.services.license_service import LicenseService
from app.services.user_service import UserService
from app.ui.components.forms.login_form import LoginForm
from app.data.database import get_db_session
from app.constants import (
    ADMIN_ROLE, ADMIN_DASHBOARD_ROUTE,
    EMPLOYEE_DASHBOARD_ROUTE, EMPLOYEE_ROLE,
    SALESPERSON_DASHBOARD_ROUTE, SALESPERSON_ROLE,
    LOGIN_ROUTE
)
from app.core.models import User
from app.ui.components.common.appbar_factory import create_appbar # Import AppBar factory
from app.config import APP_TITLE # Use APP_TITLE from config

class LoginView(ft.Container):
    def __init__(self, page: ft.Page, router, **params):
        super().__init__(expand=True, alignment=ft.alignment.center)
        self.page = page
        self.router = router
        # Services are typically not instantiated per view, but rather passed or accessed globally/via DI.
        # For simplicity here, keeping them as instance variables if needed by methods in this view.
        self.user_service = UserService()
        self.license_service = LicenseService()
        self.auth_service = AuthService() # AuthService will be used by LoginForm

        self.page.appbar = create_appbar(
            page=self.page,
            router=self.router, # Pass router for logout
            title_text=APP_TITLE, # Use app title from config
            show_logout_button=False, # No logout button on login screen
            show_user_info=False,     # No user info on login screen
            show_license_status=False # No license status on login screen
        )
        
        self.login_form_component = LoginForm(page=self.page, on_login_success=self._handle_login_success)
        # current_form_container is now self.login_form_component
        self.content = self._build_layout()

    def _build_layout(self) -> ft.Column:
        return ft.Column(
            [
                ft.Container(
                    content=ft.Icon(
                        ft.Icons.LOCK_PERSON_OUTLINED,
                        color=ft.Colors.BLUE_GREY_300, # Use a theme-aware color if possible
                        size=80,
                    ),
                    padding=ft.padding.only(bottom=20),
                ),
                ft.Container(
                    content=self.login_form_component, # The LoginForm instance
                    padding=30,
                    border_radius=ft.border_radius.all(12),
                    bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLACK), # Subtle background for the form card
                    # Use theme surface color if available, e.g., self.page.theme.surfaceVariant
                    shadow=ft.BoxShadow(
                        spread_radius=1, blur_radius=15,
                        color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK26),
                        offset=ft.Offset(0, 5),
                    ),
                    width=400, # Fixed width for the login card
                ),
                ft.Container(
                    content=ft.Text(
                        "© 2025 Anuj Patel · All Rights Reserved · Built using Python and Flet",
                        size=12,
                        color=ft.Colors.GREY_500, # Softer color
                        text_align=ft.TextAlign.CENTER,
                    ),
                    alignment=ft.alignment.center,
                    padding=10,
                    margin=ft.margin.only(top=30), # More space from form
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20, # Spacing between elements in the Column
            expand=True,
        )

    def _handle_login_success(self, user: User): # Renamed from on_login_success
        # This method is called by LoginForm upon successful authentication
        user_params = {"current_user": user} # Params for the next view
        user_role = self.auth_service.get_user_role(user) # AuthService already used by LoginForm

        license_activated = False # Default
        try:
            with get_db_session() as db:
                license_activated = self.license_service.get_license_status(db)
        except Exception as e:
            print(f"Error fetching license status: {e}")
            # Show error to user, prevent login, or proceed with license_activated = False
            self.page.open(ft.SnackBar(ft.Text("Could not verify license status. Please try again."), open=True, bgcolor=ft.Colors.ERROR))
            return # Stay on login page

        user_params["license_status"] = license_activated

        # Route based on role and license status
        if user_role == SALESPERSON_ROLE:
            self.router.navigate_to(SALESPERSON_DASHBOARD_ROUTE, **user_params)
        elif license_activated: # Admin or Employee require active license
            if user_role == ADMIN_ROLE:
                self.router.navigate_to(ADMIN_DASHBOARD_ROUTE, **user_params)
            elif user_role == EMPLOYEE_ROLE:
                self.router.navigate_to(EMPLOYEE_DASHBOARD_ROUTE, **user_params)
            else: # Should not happen with defined roles
                self.page.open(ft.SnackBar(ft.Text(f"Unknown user role '{user_role}'. Access denied."), open=True, bgcolor=ft.Colors.ERROR))
                # Potentially log this unexpected state
                # self.router.navigate_to(LOGIN_ROUTE) # Fallback to login
        else: # Admin/Employee tried to log in with inactive license
            self.page.open(
                ft.SnackBar(
                    content=ft.Text("License not active. Please contact your salesperson to activate."),
                    open=True, duration=5000 # Longer duration for important message
                )
            )
            # User stays on login page. LoginForm will clear fields or user can retry.

# -------- File Separator --------

# Filename: app/ui/views/salesperson_dashboard_view.py
import flet as ft

from app.constants import LOGIN_ROUTE, SALESPERSON_ROLE, ADMIN_ROLE, EMPLOYEE_ROLE, MANAGED_USER_ROLES
from app.core.models import User
from app.core.exceptions import ValidationError, DatabaseError
from app.services.license_service import LicenseService
from app.services.user_service import UserService
from app.data.database import get_db_session
from app.ui.components.tables.users_table import UsersTable # UsersTable (now PaginatedDataTable)
from app.ui.components.common.appbar_factory import create_appbar # AppBar Factory
from app.ui.components.common.dialog_factory import create_form_dialog # Form Dialog Factory


class SalesPersonDashboardView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user: User, license_status: bool, **params):
        super().__init__(expand=True, padding=20)
        self.page = page
        self.router = router
        self.current_user = current_user
        self.license_service = LicenseService()
        self.user_service = UserService()

        self.license_activated = license_status # Initial status from login

        self.page.appbar = create_appbar(
            page=self.page,
            router=self.router,
            title_text="Salesperson Dashboard",
            current_user=self.current_user, # Show current user
            # License status will be shown by the dedicated UI element below
            show_license_status=False,
            show_user_info=True
        )

        # --- UI Components ---
        self.users_table_component = UsersTable(
            page=self.page,
            user_service=self.user_service,
            initial_roles_to_display=[ADMIN_ROLE, EMPLOYEE_ROLE, SALESPERSON_ROLE], # Salesperson sees all
            on_data_changed_callback=self._handle_table_data_change
        )

        self.license_status_label = ft.Text(weight=ft.FontWeight.BOLD)
        self.license_action_button = ft.FilledButton(
            on_click=self._toggle_license,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
        )
        
        self.content = self._build_body()
        self._update_license_ui_elements() # Initial UI setup for license status
        self.users_table_component.refresh_data_and_ui() # Load user data

    def _get_license_status_string(self) -> str:
        return "Active" if self.license_activated else "Inactive"

    def _update_license_ui_elements(self):
        status_string = self._get_license_status_string()
        self.license_status_label.value = f"License Status: {status_string}"
        self.license_status_label.color = ft.Colors.GREEN_ACCENT_700 if self.license_activated else ft.Colors.RED_ACCENT_700

        if self.license_activated:
            self.license_action_button.text = "Deactivate License"
            self.license_action_button.icon = ft.Icons.KEY_OFF_ROUNDED
            self.license_action_button.tooltip = "Deactivate the current license"
            self.license_action_button.style.bgcolor = ft.Colors.RED_ACCENT_100 # type: ignore
            self.license_action_button.style.color = ft.Colors.RED_ACCENT_700 # type: ignore
        else:
            self.license_action_button.text = "Activate License"
            self.license_action_button.icon = ft.Icons.KEY_ROUNDED
            self.license_action_button.tooltip = "Activate a new license"
            self.license_action_button.style.bgcolor = ft.Colors.GREEN_ACCENT_100 # type: ignore
            self.license_action_button.style.color = ft.Colors.GREEN_ACCENT_700 # type: ignore

        if self.license_status_label.page: self.license_status_label.update()
        if self.license_action_button.page: self.license_action_button.update()
        # No page.update() here, let the caller update the page if necessary

    def _toggle_license(self, e):
        new_status = not self.license_activated
        try:
            with get_db_session() as db:
                self.license_service.set_license_status(db, new_status)
            self.license_activated = new_status # Update state only on success
            self._update_license_ui_elements()
            self.page.open(
                ft.SnackBar(ft.Text(f"License successfully {'activated' if new_status else 'deactivated'}."), open=True)
            )
        except DatabaseError as ex:
            self.page.open(
                ft.SnackBar(ft.Text(f"Error updating license: {ex.message}"), open=True, bgcolor=ft.Colors.ERROR)
            )
        except Exception as ex_general: # Catch any other unexpected error
            self.page.open(
                ft.SnackBar(ft.Text(f"An unexpected error occurred: {ex_general}"), open=True, bgcolor=ft.Colors.ERROR)
            )
        if self.page: self.page.update() # Update page to reflect UI changes

    def _handle_add_user_click(self, e):
        self._open_add_user_dialog()

    def _close_active_dialog(self, e=None):
        if self.page.dialog:
            self.page.close(self.page.dialog) # Use new Flet API
            # self.page.dialog = None # Dialog is removed from page.dialog automatically
            self.page.update()

    def _open_add_user_dialog(self):
        # Form fields for the dialog
        username_field = ft.TextField(label="Username", autofocus=True, border_radius=8)
        password_field = ft.TextField(label="Password", password=True, can_reveal_password=True, border_radius=8)
        confirm_password_field = ft.TextField(label="Confirm Password", password=True, can_reveal_password=True, border_radius=8)
        role_options = [ft.dropdown.Option(role, role.capitalize()) for role in MANAGED_USER_ROLES]
        role_dropdown = ft.Dropdown(label="Role", options=role_options, value=ADMIN_ROLE, border_radius=8) # Default to Admin
        error_text_add = ft.Text(visible=False, color=ft.Colors.RED_700)

        form_column = ft.Column(
            [username_field, password_field, confirm_password_field, role_dropdown, error_text_add],
            tight=True, spacing=15, scroll=ft.ScrollMode.AUTO,
        )

        # Save handler needs access to these fields
        def _save_new_user_handler(e):
            error_text_add.value = ""
            error_text_add.visible = False
            # error_text_add.update() # Update will be handled by page.update()

            username = username_field.value.strip() if username_field.value else ""
            password = password_field.value if password_field.value else ""
            confirm_password = confirm_password_field.value if confirm_password_field.value else ""
            role = role_dropdown.value

            try:
                if not username or not password or not role: # Basic check
                    raise ValidationError("All fields (Username, Password, Role) are required.")
                # More specific validation (e.g., password length) is in UserService
                
                with get_db_session() as db:
                    self.user_service.create_user(db, username, password, role)
                
                self._close_active_dialog() # Close dialog first
                self.page.open(ft.SnackBar(ft.Text(f"User '{username}' created successfully!"), open=True))
                self.users_table_component.refresh_data_and_ui() # Refresh table
            except (ValidationError, DatabaseError) as ex:
                error_text_add.value = str(ex.message if hasattr(ex, 'message') else ex)
                error_text_add.visible = True
            except Exception as ex_general:
                error_text_add.value = f"An unexpected error occurred: {ex_general}"
                error_text_add.visible = True
            
            # error_text_add.update() # Update will be handled by page.update()
            if self.page: self.page.update() # Update dialog content (e.g., show error)

        add_user_dialog = create_form_dialog(
            page=self.page,
            title_text="Add New User",
            form_content_column=form_column,
            on_save_callback=_save_new_user_handler,
            on_cancel_callback=self._close_active_dialog,
            min_width=400 # Ensure dialog is wide enough
        )
        self.page.dialog = add_user_dialog
        self.page.open(self.page.dialog)


    def _handle_table_data_change(self):
        # This callback is from UsersTable (PaginatedDataTable) after its data changes.
        # Could be used to update aggregate counts or other UI elements on this dashboard
        # if there were any that depended on the raw user list.
        # For now, it's a placeholder.
        # print("SalesPersonDashboardView: UsersTable data changed.")
        pass


    def _build_body(self) -> ft.Column:
        welcome_message_text = "Salesperson Controls"
        if self.current_user and self.current_user.username:
            welcome_message_text = f"Welcome, {self.current_user.username} (Salesperson)!"

        license_section = ft.Card(
            elevation=4,
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("License Management", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD),
                        ft.Row(
                            [self.license_status_label, self.license_action_button],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER
                        ),
                    ], spacing=10,
                ),
                padding=20, border_radius=ft.border_radius.all(8), bgcolor=ft.Colors.WHITE70,
            )
        )

        user_management_section = ft.Card(
            elevation=4,
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("User Account Management", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD, expand=True),
                                ft.FilledButton(
                                    "Add New User", icon=ft.Icons.PERSON_ADD_ALT_1_ROUNDED,
                                    on_click=self._handle_add_user_click,
                                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        self.users_table_component, # The UsersTable instance
                    ], spacing=15,
                ),
                padding=20, border_radius=ft.border_radius.all(8), expand=True, bgcolor=ft.Colors.WHITE70,
            ),
            expand=True # Card expands
        )

        # Layout: Center content if page is wide, otherwise let it fill.
        # Using a Column with horizontal_alignment and a max_width container for the content.
        centered_content_column = ft.Column(
            [
                ft.Text(welcome_message_text, style=ft.TextThemeStyle.HEADLINE_MEDIUM, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT), # Spacer
                license_section,
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT), # Spacer
                user_management_section,
            ],
            spacing=20,
            expand=True, # Column itself expands vertically
            # horizontal_alignment=ft.CrossAxisAlignment.CENTER, # Center its children (cards)
            scroll=ft.ScrollMode.ADAPTIVE, # Allow vertical scroll for the whole dashboard content
        )
        
        return ft.Container( # Outer container to control width and alignment
            content=centered_content_column,
            width=self.page.width * 0.7 if self.page.width and self.page.width > 800 else None, # Max width for content area
            # max_width=800, # Example fixed max width
            alignment=ft.alignment.top_center, # Center the content column on the page
            expand=True,
        )

    # Logout handled by appbar_factory
    # def logout(self, e):
    #     self.current_user = None
    #     self.router.navigate_to(LOGIN_ROUTE)

# -------- File Separator --------

# Filename: app/ui/views/__init__.py


# -------- File Separator --------

# Filename: app/ui/views/admin/book_management.py
import flet as ft

from app.constants import LOGIN_ROUTE, ADMIN_DASHBOARD_ROUTE
from app.core.models import User # Import User model for type hinting
from app.ui.components.common.appbar_factory import create_appbar # Import AppBar factory


class BookManagementView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user: User, license_status: bool,
                 previous_view_route: str = ADMIN_DASHBOARD_ROUTE, # Default previous route
                 previous_view_params: dict = None, # Params to reconstruct previous view
                 **params):
        super().__init__(expand=True)
        self.page = page
        self.router = router
        self.current_user = current_user
        self.license_status = license_status

        self.previous_view_route = previous_view_route
        # Ensure previous_view_params is a dict, even if None is passed
        self.previous_view_params = previous_view_params if previous_view_params is not None else {}

        self.page.appbar = create_appbar(
            page=self.page,
            router=self.router,
            title_text="Admin > Book Management", # More specific title
            current_user=self.current_user,
            license_status=self.license_status,
            leading_widget=ft.IconButton( # Back button
                icon=ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                tooltip="Go Back",
                icon_color=ft.Colors.WHITE,
                on_click=self._go_back,
            )
        )
        self.content = self._build_body()

    def _go_back(self, e):
        """Handles the click event for the back button, navigating to the stored previous view."""
        # Pass current_user and license_status if they are part of previous_view_params structure
        # The ADMIN_DASHBOARD_ROUTE expects current_user and license_status
        nav_params = {**self.previous_view_params} # Start with stored params
        if "current_user" not in nav_params and self.current_user: # Ensure current_user is passed back if needed
             nav_params["current_user"] = self.current_user
        if "license_status" not in nav_params and self.license_status is not None:
             nav_params["license_status"] = self.license_status
        
        self.router.navigate_to(self.previous_view_route, **nav_params)


    def _build_body(self) -> ft.Column: # Return type hint
        # Placeholder content for Book Management
        # This area would typically include a table for books, add/edit buttons, search, etc.
        # For example, a PaginatedDataTable for books.

        # Example: Add New Book Button (placeholder action)
        add_book_button = ft.FilledButton(
            "Add New Book",
            icon=ft.Icons.ADD_CIRCLE_OUTLINE_ROUNDED,
            on_click=lambda e: self.page.open(ft.SnackBar(ft.Text("Add New Book - Not Implemented"), open=True)),
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
        )

        # Example: Search field (placeholder)
        search_field = ft.TextField(
            label="Search Books (e.g., Book Number, Game Name)",
            hint_text="Type to search books...",
            prefix_icon=ft.Icons.SEARCH,
            border_radius=8,
            expand=True,
            # on_change=self._on_book_search_change, # Would need a handler
        )

        # Placeholder for a table or list of books
        books_display_area = ft.Container(
            content=ft.Text("Book listing area (e.g., a table of books will be here).", italic=True),
            padding=20,
            border=ft.border.all(1, ft.Colors.OUTLINE), # type: ignore
            border_radius=ft.border_radius.all(8),
            expand=True,
        )


        return ft.Column(
            controls=[
                ft.Text("Book Management", style=ft.TextThemeStyle.HEADLINE_MEDIUM, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Row([search_field, add_book_button], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                books_display_area,
                # Additional controls for book management...
            ],
            alignment=ft.MainAxisAlignment.START, # Align content to the top
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH, # Stretch children like search row
            spacing=20, # Spacing between elements
            expand=True,
            padding=20 # Padding for the overall body content
        )

    # Logout handled by appbar_factory
    # def logout(self, e):
    #     self.current_user = None
    #     self.router.navigate_to(LOGIN_ROUTE)

# -------- File Separator --------

# Filename: app/ui/views/admin/game_management.py
import threading # Keep for search debounce if not fully handled by component
import flet as ft

from app.constants import LOGIN_ROUTE, ADMIN_DASHBOARD_ROUTE, \
    REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER
from app.core import ValidationError, DatabaseError, GameNotFoundError # Added GameNotFoundError
from app.core.models import User # For type hinting
from app.data.database import get_db_session
from app.services.game_service import GameService
from app.ui.components.tables.games_table import GamesTable # Specific GamesTable
from app.ui.components.widgets.number_decimal_input import NumberDecimalField
from app.ui.components.common.appbar_factory import create_appbar # AppBar Factory
from app.ui.components.common.search_bar_component import SearchBarComponent # Search Bar Component
from app.ui.components.common.dialog_factory import create_form_dialog # Form Dialog Factory


class GameManagementView(ft.Container):
    def __init__(self, page: ft.Page, router, current_user: User, license_status: bool,
                 previous_view_route: str = ADMIN_DASHBOARD_ROUTE,
                 previous_view_params: dict = None,
                 **params):
        super().__init__(expand=True, padding=20)
        self.game_service = GameService()
        self.page = page
        self.router = router
        self.current_user = current_user
        self.license_status = license_status

        self.total_games_widget = ft.Text("", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD)
        self.active_games_widget = ft.Text("", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)
        self.expired_games_widget = ft.Text("", style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_700)

        self.previous_view_route = previous_view_route
        self.previous_view_params = previous_view_params if previous_view_params is not None else {}

        self.games_table_component = GamesTable( # This is now the refactored GamesTable
            page=self.page,
            game_service=self.game_service, # Pass game_service
            on_data_changed_stats=self._handle_table_data_stats_change,
        )
        
        self.search_bar = SearchBarComponent(
            on_search_changed=self._on_search_term_changed,
            label="Search Games (Name, No., Price, Tickets, Value)",
            # debounce_time_ms=300 # Default is 500ms
        )

        self.page.appbar = create_appbar(
            page=self.page,
            router=self.router,
            title_text="Admin > Game Management",
            current_user=self.current_user,
            license_status=self.license_status,
            leading_widget=ft.IconButton(
                icon=ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                tooltip="Go Back", icon_color=ft.Colors.WHITE, on_click=self._go_back,
            )
        )
        self.content = self._build_body()
        self.games_table_component.refresh_data_and_ui() # Initial data load for the table

    def _on_search_term_changed(self, search_term: str):
        """Callback for the SearchBarComponent."""
        # The PaginatedDataTable (GamesTable) handles its own search term storage
        self.games_table_component.refresh_data_and_ui(search_term=search_term)
        # Stats are updated via the on_data_changed_stats callback in GamesTable

    def _go_back(self, e):
        nav_params = {**self.previous_view_params}
        if "current_user" not in nav_params and self.current_user:
             nav_params["current_user"] = self.current_user
        if "license_status" not in nav_params and self.license_status is not None:
             nav_params["license_status"] = self.license_status
        self.router.navigate_to(self.previous_view_route, **nav_params)


    def _build_body(self) -> ft.Column:
        stats_row = ft.Row(
            [self.total_games_widget, self.active_games_widget, self.expired_games_widget],
            alignment=ft.MainAxisAlignment.START, spacing=30, # More spacing for stats
        )

        actions_row = ft.Row(
            [
                self.search_bar, # The SearchBarComponent instance
                ft.FilledButton(
                    "Add New Game", icon=ft.Icons.GAMEPAD_OUTLINED, # Consistent icon
                    on_click=self._handle_add_game_click,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN, # Space out search and button
        )

        game_management_section = ft.Card(
            elevation=2, # Subtle elevation
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Game Configuration & Overview", style=ft.TextThemeStyle.HEADLINE_SMALL, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                        ft.Divider(height=15),
                        stats_row,
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        actions_row, # Combined search and add button row
                        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        self.games_table_component, # The GamesTable instance
                    ],
                    spacing=15,
                ),
                padding=20, border_radius=ft.border_radius.all(8), expand=True,
                # bgcolor=ft.Colors.WHITE70, # Consider removing for default card color from theme
            ),
            expand=True
        )
        return ft.Column(
            [game_management_section],
            expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            # scroll=ft.ScrollMode.ADAPTIVE, # Table itself is scrollable if needed
        )

    def _close_active_dialog(self, e=None):
        if self.page.dialog:
            self.page.close(self.page.dialog)
            self.page.update()


    def _handle_add_game_click(self, e):
        # Form fields for the dialog
        game_name_field = ft.TextField(label="Game Name", autofocus=True, border_radius=8)
        price_field = NumberDecimalField( # Expects float input, converts to cents
            label="Price (e.g., $1.00)", hint_text="e.g., 1.00 or 0.50",
            is_money_field=True, currency_symbol="$", is_integer_only=False, border_radius=8,
        )
        total_tickets_field = NumberDecimalField(label="Total Tickets", is_integer_only=True, border_radius=8, hint_text="e.g., 150")
        ticket_order_options = [ft.dropdown.Option(order, order.capitalize()) for order in [REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER]]
        ticket_order_dropdown = ft.Dropdown(label="Ticket Order", options=ticket_order_options, value=REVERSE_TICKET_ORDER, border_radius=8)
        game_number_field = NumberDecimalField(label="Game No.", is_integer_only=True, border_radius=8, hint_text="e.g., 453")
        error_text_add = ft.Text(visible=False, color=ft.Colors.RED_700)

        form_column = ft.Column(
            [game_name_field, price_field, total_tickets_field, ticket_order_dropdown, game_number_field, error_text_add],
            tight=True, spacing=15, scroll=ft.ScrollMode.AUTO,
        )

        # Save handler needs access to these fields
        def _save_new_game_handler(ev): # Renamed event arg
            error_text_add.value = ""
            error_text_add.visible = False
            # error_text_add.update() # page.update will cover this

            game_name = game_name_field.value.strip() if game_name_field.value else ""
            price_float = price_field.get_value_as_float() # Get float value (e.g., 1.50)
            price_cents = int(price_float * 100) if price_float is not None else None

            total_tickets = total_tickets_field.get_value_as_int()
            order = ticket_order_dropdown.value
            game_number = game_number_field.get_value_as_int()

            try:
                # Validation (some is also in service layer)
                if not game_name: raise ValidationError("Game Name is required.")
                if price_cents is None: raise ValidationError("Valid Price is required (e.g., 1.00).")
                if total_tickets is None or total_tickets <= 0: raise ValidationError("Total Tickets must be a positive number.")
                if not order: raise ValidationError("Ticket Order is required.")
                if game_number is None or game_number <= 0: raise ValidationError("Game Number must be a positive number.")

                with get_db_session() as db:
                    self.game_service.create_game(db, game_name, price_cents, total_tickets, game_number, order)
                
                self._close_active_dialog() # Close dialog first
                self.page.open(ft.SnackBar(ft.Text(f"Game '{game_number} -- {game_name}' created successfully!"), open=True))
                self.games_table_component.refresh_data_and_ui(self.search_bar.get_value()) # Refresh table
            except (ValidationError, DatabaseError, GameNotFoundError) as ex: # Added GameNotFoundError
                error_text_add.value = str(ex.message if hasattr(ex, 'message') else ex)
                error_text_add.visible = True
            except Exception as ex_general:
                error_text_add.value = f"An unexpected error occurred: {ex_general}"
                error_text_add.visible = True
            
            # error_text_add.update() # page.update will cover this
            if self.page: self.page.update() # Update dialog content (e.g., show error)

        add_game_dialog = create_form_dialog(
            page=self.page,
            title_text="Add New Game",
            form_content_column=form_column,
            on_save_callback=_save_new_game_handler,
            on_cancel_callback=self._close_active_dialog,
            min_width=450 # Slightly wider for game form
        )
        self.page.dialog = add_game_dialog
        self.page.open(self.page.dialog)

    def _handle_table_data_stats_change(self, total_games: int, active_games: int, expired_games: int):
        """Callback from GamesTable when its underlying (unfiltered) data stats change."""
        self.total_games_widget.value = f"Total Games: {total_games}"
        self.active_games_widget.value = f"Active: {active_games}"
        self.expired_games_widget.value = f"Expired: {expired_games}"
        
        # Update widgets if they are on the page
        if self.total_games_widget.page: self.total_games_widget.update()
        if self.active_games_widget.page: self.active_games_widget.update()
        if self.expired_games_widget.page: self.expired_games_widget.update()
        # No full page.update() here to avoid conflicts if dialog is open.
        # The view containing these stats should update itself if necessary.

# -------- File Separator --------

# Filename: app/ui/views/admin/__init__.py


# -------- File Separator --------

# Filename: app/utils/helpers.py
# This file is currently empty. It could be used for utility functions
# that don't fit neatly into other categories, for example:
# - Date/time formatting utilities
# - String manipulation helpers
# - Currency formatting functions (if not handled by widgets directly)
# - Complex validation logic shared across multiple services or UI components

# Example (if needed later):
# import datetime

# def format_currency(amount_in_cents: int, symbol: str = "$") -> str:
#     if amount_in_cents is None:
#         return ""
#     return f"{symbol}{amount_in_cents / 100:.2f}"

# def format_datetime_for_display(dt: Optional[datetime.datetime]) -> str:
#     if dt is None:
#         return "N/A"
#     return dt.strftime("%Y-%m-%d %I:%M %p")


# -------- File Separator --------

# Filename: app/utils/__init__.py

```