# Filename: app/ui/components/common/paginated_data_table.py
from math import ceil
from typing import List, Callable, Optional, Any, Dict, TypeVar, Generic
import flet as ft
import datetime
import inspect

from app.data.database import get_db_session

T = TypeVar('T')

class PaginatedDataTable(ft.Container, Generic[T]):
    def __init__(
            self,
            page: ft.Page,
            fetch_all_data_func: Callable[[Any], List[T]],
            column_definitions: List[Dict[str, Any]],
            action_cell_builder: Optional[Callable[[T, 'PaginatedDataTable[T]'], ft.DataCell]],
            rows_per_page: int = 10,
            initial_sort_key: Optional[str] = None,
            initial_sort_ascending: bool = True,
            on_data_stats_changed: Optional[Callable[[int, int, int], None]] = None,
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
        self._displayed_data: List[T] = []

        self._current_sort_column_key: Optional[str] = initial_sort_key
        self._current_sort_ascending: bool = initial_sort_ascending
        self._current_page_number: int = 1
        self._last_search_term: str = ""

        self.datatable = ft.DataTable(
            columns=[],
            rows=[],
            column_spacing=20,
            expand=True,
            vertical_lines=ft.BorderSide(width=0.5, color=ft.Colors.with_opacity(0.15, ft.Colors.ON_SURFACE)),
            horizontal_lines=ft.BorderSide(width=0.5, color=ft.Colors.with_opacity(0.1, ft.Colors.ON_SURFACE)),
            sort_ascending=self._current_sort_ascending,
            heading_row_height=heading_row_height,
            data_row_max_height=data_row_max_height,
        )
        self._initialize_columns()

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
            else:
                self._current_sort_column_key = None


    def _handle_column_sort(self, e: ft.ControlEvent):
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
            self._filter_and_sort_displayed_data(self._last_search_term)
        else:
            print(f"Warning: Sort key not found for column label '{clicked_label}'")


    def _get_sort_value_for_item(self, item: T, sort_key: str) -> Any:
        """
        Extracts a value from an item for sorting.
        Handles None values by returning type-appropriate min/max values.
        """
        col_def = self._get_column_def_by_key(sort_key)
        raw_value = getattr(item, sort_key, None)

        if col_def and col_def.get('custom_sort_value_getter'):
            return col_def['custom_sort_value_getter'](item)

        if isinstance(raw_value, str):
            return raw_value.lower() # Case-insensitive sort for strings

        if raw_value is None:
            # Get the type of the attribute from a non-None item if possible,
            # or rely on a hint from column_definitions if provided.
            # For simplicity here, we'll check if the sort_key corresponds to known date fields.
            # A more robust solution might involve passing a 'data_type' in column_definitions.

            # Specifically handle None for datetime fields
            if sort_key in ["created_date", "expired_date", "activate_date", "finish_date", "date"]: # Add any other date keys
                return datetime.datetime.min if self._current_sort_ascending else datetime.datetime.max
            else: # Default for other types
                return float('-inf') if self._current_sort_ascending else float('inf')

        # If raw_value is already a datetime, it's fine
        if isinstance(raw_value, datetime.datetime):
            return raw_value

        # For other types (numbers, booleans), return as is
        return raw_value



    def _filter_and_sort_displayed_data(self, search_term: str = ""):
        self._last_search_term = search_term.lower().strip()

        if not self._last_search_term or not self.default_search_enabled:
            self._displayed_data = list(self._all_unfiltered_data)
        else:
            self._displayed_data = []
            searchable_keys = [cd['key'] for cd in self.column_definitions if cd.get('searchable', True)]
            for item in self._all_unfiltered_data:
                found = False
                for key in searchable_keys:
                    value = getattr(item, key, None)
                    col_def_for_key = self._get_column_def_by_key(key)
                    display_formatter = col_def_for_key.get('display_formatter') if col_def_for_key else None

                    str_value = ""
                    if display_formatter:
                        # Check number of parameters the formatter expects from the caller
                        num_params = 0
                        if callable(display_formatter):
                            try:
                                num_params = len(inspect.signature(display_formatter).parameters)
                            except ValueError: # Some callables might not have a clear signature (e.g. built-in)
                                pass

                        formatted_control: Optional[ft.Control] = None
                        if num_params == 2: # Assumes (value, item)
                            formatted_control = display_formatter(value, item)
                        elif num_params == 1: # Assumes (value)
                            formatted_control = display_formatter(value)
                        else: # Fallback or if not a standard formatter
                            formatted_control = ft.Text(str(value) if value is not None else "")


                        if isinstance(formatted_control, ft.Text):
                            str_value = str(formatted_control.value).lower()
                        elif value is not None: # Fallback if formatter returns non-Text or complex Control
                            str_value = str(value).lower()
                    elif value is not None:
                        str_value = str(value).lower()

                    if self._last_search_term in str_value:
                        found = True
                        break
                if found:
                    self._displayed_data.append(item)

        if self._current_sort_column_key:
            sort_key_attr = self._current_sort_column_key
            self._displayed_data.sort(
                key=lambda item_to_sort: self._get_sort_value_for_item(item_to_sort, sort_key_attr),
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
            if formatter and callable(formatter): # Ensure formatter is callable
                try:
                    # Use inspect.signature to determine how to call the formatter
                    sig = inspect.signature(formatter)
                    num_params = len(sig.parameters)

                    if num_params == 2:  # Expects (value, item)
                        cell_content = formatter(raw_value, item)
                    elif num_params == 1:  # Expects (value)
                        cell_content = formatter(raw_value)
                    else:
                        # This case can happen if a method is passed without 'self' being bound,
                        # or if the signature is unusual.
                        # For instance methods like self._format_expired_date_cell,
                        # len(inspect.signature(self._format_expired_date_cell).parameters) is 2.
                        # So this 'else' should ideally not be hit for well-defined formatters.
                        # print(f"Warning: Formatter for key {key} has an unexpected signature: {sig}. Defaulting display.")
                        cell_content = ft.Text(str(raw_value) if raw_value is not None else "", size=12.5)
                except ValueError: # E.g. for built-in functions that inspect.signature might not handle as expected
                    # print(f"Warning: Could not inspect signature for formatter of key {key}. Attempting call with value only.")
                    try:
                        cell_content = formatter(raw_value) # Try calling with just value
                    except TypeError:
                        # print(f"Error: Formatter for key {key} failed. Defaulting display.")
                        cell_content = ft.Text(str(raw_value) if raw_value is not None else "", size=12.5)

                except Exception as e:
                    # print(f"Error applying formatter for key {key}: {e}. Defaulting display.")
                    cell_content = ft.Text(str(raw_value) if raw_value is not None else "", size=12.5)
            else:
                cell_content = ft.Text(str(raw_value) if raw_value is not None else "", size=12.5)
            cells.append(ft.DataCell(cell_content))

        if self.action_cell_builder:
            action_cell = self.action_cell_builder(item, self)
            cells.append(action_cell)

        return ft.DataRow(cells=cells, color={"hovered": ft.Colors.with_opacity(0.05, ft.Colors.PRIMARY)})


    def _update_datatable_rows(self):
        if not self.datatable.columns:
            self._initialize_columns() # Ensures self.datatable.columns is populated

        num_defined_columns = len(self.datatable.columns) if self.datatable.columns else 0

        if not self._displayed_data:
            if num_defined_columns > 0:
                # This is the row displayed when there's no data.
                # It needs one DataCell for each defined DataColumn.

                # Create the first cell with the "No data" message.
                no_data_text_widget = ft.Text(
                    self.no_data_message,
                    italic=True,
                    text_align=ft.TextAlign.CENTER,
                )
                first_cell = ft.DataCell(no_data_text_widget)
                # Set its colspan to span all columns.
                first_cell.colspan = num_defined_columns

                # Initialize the list of cells for this row with the first cell.
                cells_for_no_data_row = [first_cell]

                # Add (N-1) empty DataCells to make up the total column count.
                # These cells are structurally required by DataTable, even if the first cell spans them.
                # They won't take up visual space if the colspan of the first cell is correctly rendered.
                for _ in range(1, num_defined_columns):
                    cells_for_no_data_row.append(ft.DataCell(ft.Text(""))) # Empty content

                self.datatable.rows = [ft.DataRow(cells=cells_for_no_data_row)]
            else:
                # No columns defined, so no rows can be added.
                self.datatable.rows = []
        else:
            # Logic for when there IS data (this part should be okay)
            start_index = (self._current_page_number - 1) * self.rows_per_page
            end_index = start_index + self.rows_per_page
            paginated_items = self._displayed_data[start_index:end_index]
            self.datatable.rows = [self._build_datarow(item) for item in paginated_items]

        self._update_pagination_controls()
        if self.page and self.page.controls: # Ensure page and controls exist before updating
            self.page.update()


    def _update_pagination_controls(self):
        if not self.page_info_text.page or not self.show_pagination:
            return

        total_rows = len(self._displayed_data)
        total_pages = ceil(total_rows / self.rows_per_page) if total_rows > 0 else 1
        total_pages = max(1, total_pages)

        self.page_info_text.value = f"Page {self._current_page_number} of {total_pages}"
        self.prev_button.disabled = self._current_page_number == 1
        self.next_button.disabled = self._current_page_number == total_pages

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
        if search_term is None:
            search_term = self._last_search_term
        else:
            self._last_search_term = search_term

        try:
            with get_db_session() as db:
                self._all_unfiltered_data = self.fetch_all_data_func(db)

            if self.on_data_stats_changed:
                # This is a generic hook. The specific stats calculation and call
                # is now handled in the GamesTable override of _filter_and_sort_displayed_data.
                pass

            self._current_page_number = 1
            self._filter_and_sort_displayed_data(search_term)

        except Exception as e:
            print(f"Error refreshing data for table: {e}")
            if self.page:
                self.page.open(ft.SnackBar(ft.Text(f"Error loading data: {type(e).__name__}"), open=True, bgcolor=ft.Colors.ERROR))


    def get_current_search_term(self) -> str:
        return self._last_search_term

    def close_dialog_and_refresh(self, dialog_to_close: Optional[ft.AlertDialog] = None, success_message: Optional[str] = None):
        current_dialog = dialog_to_close if dialog_to_close else self.page.dialog # type: ignore
        if current_dialog and self.page.dialog == current_dialog :
            self.page.close(current_dialog)

        if success_message and self.page:
            self.page.open(ft.SnackBar(ft.Text(success_message), open=True))
        self.refresh_data_and_ui(self._last_search_term)

    def show_error_snackbar(self, message: str):
        if self.page:
            self.page.open(ft.SnackBar(ft.Text(message), open=True, bgcolor=ft.Colors.ERROR))