import flet as ft
from typing import List, Callable, Optional, Dict
from app.core.models import Book as BookModel
from app.services.sales_entry_service import SalesEntryService
from app.data.database import get_db_session
from .sales_entry_item_data import SalesEntryItemData

class SalesEntryItemsTable(ft.Container):
    def __init__(self,
                 page_ref: ft.Page,
                 sales_entry_service: SalesEntryService,
                 on_item_change_callback: Callable[[SalesEntryItemData], None],
                 on_all_items_loaded_callback: Callable[[List[SalesEntryItemData]], None]
                 ):
        super().__init__(expand=True)
        self.page = page_ref
        self.sales_entry_service = sales_entry_service
        self.on_item_change_callback = on_item_change_callback
        self.on_all_items_loaded_callback = on_all_items_loaded_callback

        self.sales_items_data_list: List[SalesEntryItemData] = []
        self.sales_items_map: Dict[str, SalesEntryItemData] = {}

        self.datatable = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Book Details", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Price", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Current Ticket", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("New Ticket #", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Tickets Sold", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Amount", weight=ft.FontWeight.BOLD), numeric=True),
            ],
            rows=[],
            column_spacing=15,
            heading_row_height=40,
            data_row_max_height=55,
            expand=True,
        )
        self.content = ft.Column(
            [self.datatable],
            scroll=ft.ScrollMode.ADAPTIVE,
            expand=True
        )

    def _internal_item_change_handler(self, item_data: SalesEntryItemData):
        self.update_datarow_for_item(item_data.unique_id)
        self.on_item_change_callback(item_data)

    def load_initial_active_books(self):
        self.sales_items_data_list = []
        self.sales_items_map = {}
        initial_rows = []
        try:
            with get_db_session() as db:
                active_books: List[BookModel] = self.sales_entry_service.get_active_books_for_sales_display(db)

            for book_model in active_books:
                if book_model.id is None: continue
                item_data = SalesEntryItemData(
                    book_model=book_model,
                    on_change_callback=self._internal_item_change_handler
                )
                self.sales_items_data_list.append(item_data)
                self.sales_items_map[item_data.unique_id] = item_data
                initial_rows.append(item_data.to_datarow())

            self.datatable.rows = initial_rows
            self.on_all_items_loaded_callback(self.sales_items_data_list)
        except Exception as e:
            print(f"Error loading active books for sales table: {e}")
            self.datatable.rows = [ft.DataRow(cells=[ft.DataCell(ft.Text(f"Error loading books: {e}", color=ft.Colors.ERROR))])]

        if self.page and self.page.controls: self.page.update()


    def add_or_update_book_for_sale(self, book_model: BookModel, scanned_ticket_str: Optional[str] = None) -> Optional[SalesEntryItemData]:
        if book_model.id is None:
            error_msg = "Error: Book ID missing when adding/updating in sales table."
            if self.page: self.page.open(ft.SnackBar(ft.Text(error_msg), open=True, bgcolor=ft.Colors.ERROR))
            print(f"CRITICAL: {error_msg} - Book: {book_model.book_number}")
            return None

        unique_id = f"book-{book_model.id}"
        item_data = self.sales_items_map.get(unique_id)

        if item_data:  # Book ALREADY IN TABLE
            print(f"SalesTable: Updating existing item {unique_id} with scan: {scanned_ticket_str if scanned_ticket_str else 'No Ticket Scan'}")
            # Update the existing item_data's underlying book_model and sync critical fields
            item_data.book_model = book_model
            item_data.db_current_ticket_no = book_model.current_ticket_number
            # Game details could also be updated if they can change, but typically game_price, name, total_tickets are fixed once book is created.
            item_data.game_name = book_model.game.name if book_model.game else item_data.game_name
            item_data.game_price = book_model.game.price if book_model.game else item_data.game_price
            item_data.game_total_tickets = book_model.game.total_tickets if book_model.game else item_data.game_total_tickets
            item_data.ticket_order = book_model.ticket_order

            if scanned_ticket_str:
                item_data.update_scanned_ticket_number(scanned_ticket_str)
            else:
                # If no new scan, but book_model might have been updated (e.g. current_ticket_number from another source)
                # we should ensure calculations are based on current state.
                # SalesEntryItemData._calculate_sales() is called internally by update_scanned_ticket_number
                # or when its TextField changes. If only db_current_ticket_no changed, we might need to manually trigger.
                # For now, update_scanned_ticket_number is the main path for explicit changes.
                # An explicit _recalculate() on item_data might be useful if only db state changes.
                pass # No explicit recalculation here unless a ticket is scanned.

            self.update_datarow_for_item(unique_id)
        else:  # Book NOT IN TABLE YET
            print(f"SalesTable: Adding new item {unique_id} with scan: {scanned_ticket_str if scanned_ticket_str else 'No Ticket Scan'}")
            item_data = SalesEntryItemData(
                book_model=book_model,
                on_change_callback=self._internal_item_change_handler
            )
            # Apply scanned ticket if this is its first appearance with a scan
            if scanned_ticket_str:
                item_data.update_scanned_ticket_number(scanned_ticket_str)
            # else: # No scan, just adding the active book (e.g., from initial load or manual add without ticket)
            # SalesEntryItemData's __init__ does not call _calculate_sales, so ensure it's called.
            # However, update_scanned_ticket_number also calls _calculate_sales.
            # If no ticket, initial calculation will be 0 sold.
            # Let's ensure _calculate_sales is called to set initial state.
            item_data._calculate_sales() # Ensure initial calculation if no ticket scanned

            self.sales_items_data_list.insert(0, item_data)  # Add to top of internal list
            self.sales_items_map[unique_id] = item_data     # Add to map

            # Add new row to the ft.DataTable
            new_row = item_data.to_datarow()
            self.datatable.rows.insert(0, new_row)

            self.on_item_change_callback(item_data) # Notify view about the new item for totals

        if self.page and self.page.controls: self.page.update()
        return item_data

    def update_datarow_for_item(self, unique_item_id: str):
        item_data = self.sales_items_map.get(unique_item_id)
        if not item_data:
            print(f"SalesTable: Attempted to update non-existent item: {unique_item_id}")
            return

        try:
            # Find the index of the item in the list to update the correct ft.DataRow
            # This assumes sales_items_data_list order matches datatable.rows order
            idx_in_list = -1
            for i, current_item_data in enumerate(self.sales_items_data_list):
                if current_item_data.unique_id == unique_item_id:
                    idx_in_list = i
                    break

            if idx_in_list != -1:
                self.datatable.rows[idx_in_list] = item_data.to_datarow()
                print(f"SalesTable: Refreshed row for item {unique_item_id} at index {idx_in_list}")
            else: # Should not happen if map and list are perfectly synced
                print(f"SalesTable: Item {unique_item_id} found in map but not in list. Rebuilding all rows.")
                self.datatable.rows = [item.to_datarow() for item in self.sales_items_data_list]
        except Exception as e:
            print(f"SalesTable: Error updating datarow for {unique_item_id}: {e}. Rebuilding all rows.")
            # Fallback: rebuild all rows if specific update fails
            self.datatable.rows = [item.to_datarow() for item in self.sales_items_data_list]

        if self.page and self.page.controls: self.page.update()


    def get_all_data_items(self) -> List[SalesEntryItemData]: # Renamed for clarity
        """Returns all current SalesEntryItemData instances, regardless of processed state."""
        return self.sales_items_data_list

    def get_all_items_for_submission(self) -> List[SalesEntryItemData]:
        """Returns all current SalesEntryItemData instances that are processed for sale OR confirmed all sold."""
        return [item for item in self.sales_items_data_list if item.is_processed_for_sale or item.all_tickets_sold_confirmed]

    def get_item_by_book_id(self, book_db_id: int) -> Optional[SalesEntryItemData]:
        unique_id = f"book-{book_db_id}"
        return self.sales_items_map.get(unique_id)