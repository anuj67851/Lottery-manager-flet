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
            action_cell_builder: Optional[Callable[[T, 'PaginatedDataTable[T]'], ft.DataCell]], # Pass self for page access
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