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
        self.sales_items_map: Dict[str, SalesEntryItemData] = {} # Maps unique_id to SalesEntryItemData

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
        # When an item's internal state changes (e.g., textfield edit), update its row
        self.update_datarow_for_item(item_data.unique_id) # This will refresh the specific row
        self.on_item_change_callback(item_data) # Notify view for totals update

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
                # initial_rows.append(item_data.to_datarow()) # Rows built at the end

            # Sort by game_number, then book_number initially
            self.sales_items_data_list.sort(key=lambda x: (x.book_model.game.game_number, x.book_number))
            self.datatable.rows = [item.to_datarow() for item in self.sales_items_data_list]

            self.on_all_items_loaded_callback(self.sales_items_data_list) # Notify view
        except Exception as e:
            print(f"Error loading active books for sales table: {e}")
            self.datatable.rows = [ft.DataRow(cells=[ft.DataCell(ft.Text(f"Error loading books: {e}", color=ft.Colors.ERROR))])]

        if self.page and self.page.controls: self.page.update()


    def add_or_update_book_for_sale(self, book_model: BookModel, scanned_ticket_str: Optional[str] = None) -> Optional[SalesEntryItemData]:
        if book_model.id is None:
            # ... (error handling as before)
            return None

        unique_id = f"book-{book_model.id}"
        item_data = self.sales_items_map.get(unique_id)

        is_new_item = False
        if item_data:  # Book ALREADY IN TABLE
            print(f"SalesTable: Updating existing item {unique_id} with scan: {scanned_ticket_str if scanned_ticket_str else 'No Ticket Scan'}")
            # Remove from current position to re-insert at top
            self.sales_items_data_list = [item for item in self.sales_items_data_list if item.unique_id != unique_id]

            # Update existing item_data's model and critical fields
            item_data.book_model = book_model
            item_data.db_current_ticket_no = book_model.current_ticket_number
            item_data.game_name = book_model.game.name if book_model.game else item_data.game_name
            item_data.game_price = book_model.game.price if book_model.game else item_data.game_price
            item_data.game_total_tickets = book_model.game.total_tickets if book_model.game else item_data.game_total_tickets
            item_data.ticket_order = book_model.ticket_order

            if scanned_ticket_str:
                item_data.update_scanned_ticket_number(scanned_ticket_str) # This calls _calculate_sales and on_change_callback
            else:
                item_data._calculate_sales() # Recalculate if no scan but model might have changed

        else:  # Book NOT IN TABLE YET
            is_new_item = True
            print(f"SalesTable: Adding new item {unique_id} with scan: {scanned_ticket_str if scanned_ticket_str else 'No Ticket Scan'}")
            item_data = SalesEntryItemData(
                book_model=book_model,
                on_change_callback=self._internal_item_change_handler
            )
            if scanned_ticket_str:
                item_data.update_scanned_ticket_number(scanned_ticket_str)
            else:
                item_data._calculate_sales() # Ensure initial calculation

            self.sales_items_map[unique_id] = item_data

        # Add/Re-add item_data to the beginning of the list
        self.sales_items_data_list.insert(0, item_data)

        # Rebuild all DataTable rows to reflect the new order
        self.datatable.rows = [item.to_datarow() for item in self.sales_items_data_list]

        # Notify the main view about the change for total updates, especially if it was a new item
        if is_new_item : # Or always call if totals might change due to scan on existing item
            self.on_item_change_callback(item_data)

        if self.page and self.page.controls: self.page.update()
        return item_data

    def update_datarow_for_item(self, unique_item_id: str):
        """Updates a specific row in the DataTable if its underlying data changed."""
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
                # Re-create the DataRow for this specific item
                self.datatable.rows[idx_in_list] = item_data.to_datarow()
                print(f"SalesTable: Refreshed row for item {unique_item_id} at index {idx_in_list}")
            else:
                # This case should be less frequent if list and map are synced,
                # especially with the "move to top" logic rebuilding all rows.
                print(f"SalesTable: Item {unique_item_id} in map but not list during specific update. Rebuilding all rows.")
                self.datatable.rows = [item.to_datarow() for item in self.sales_items_data_list]

        except Exception as e:
            print(f"SalesTable: Error updating specific datarow for {unique_item_id}: {e}. Rebuilding all rows.")
            self.datatable.rows = [item.to_datarow() for item in self.sales_items_data_list]

        if self.page and self.page.controls: self.page.update()


    def get_all_data_items(self) -> List[SalesEntryItemData]:
        return self.sales_items_data_list

    def get_all_items_for_submission(self) -> List[SalesEntryItemData]:
        return [item for item in self.sales_items_data_list if item.is_processed_for_sale or item.all_tickets_sold_confirmed]

    def get_item_by_book_id(self, book_db_id: int) -> Optional[SalesEntryItemData]:
        unique_id = f"book-{book_db_id}"
        return self.sales_items_map.get(unique_id)