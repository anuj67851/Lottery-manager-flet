import flet as ft
from typing import List, Callable, Optional, Dict
from app.core.models import Book as BookModel
from app.services.sales_entry_service import SalesEntryService
from app.data.database import get_db_session
from .sales_entry_item_data import SalesEntryItemData # Relative import

class SalesEntryItemsTable(ft.Container):
    def __init__(self,
                 page_ref: ft.Page,
                 sales_entry_service: SalesEntryService,
                 on_item_change_callback: Callable[[Optional[SalesEntryItemData]], None], # Callback to SalesEntryView
                 on_all_items_loaded_callback: Callable[[List[SalesEntryItemData]], None] # Callback to SalesEntryView
                 ):
        super().__init__(expand=True)
        self.page = page_ref
        self.sales_entry_service = sales_entry_service
        self.on_item_change_callback = on_item_change_callback # This is SalesEntryView._update_totals_and_book_counts_properties
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
            rows=[], column_spacing=15, heading_row_height=40, data_row_max_height=55, expand=True,
        )
        self.content = ft.Column([self.datatable], scroll=ft.ScrollMode.ADAPTIVE, expand=True)

    def _internal_item_change_handler(self, item_data: SalesEntryItemData):
        """Called by SalesEntryItemData when its state (e.g., manual ticket entry) changes."""
        self.update_datarow_for_item(item_data.unique_id)
        self.on_item_change_callback(item_data) # Notify SalesEntryView to update its total properties
        if self.page: # Ensure page is available
            self.page.update() # THIS IS THE FIX for grand total update on manual entry

    def load_initial_active_books(self):
        self.sales_items_data_list = []
        self.sales_items_map = {}
        try:
            with get_db_session() as db:
                active_books: List[BookModel] = self.sales_entry_service.get_active_books_for_sales_display(db)
            for book_model in active_books:
                if book_model.id is None: continue
                item_data = SalesEntryItemData(
                    book_model=book_model,
                    on_change_callback=self._internal_item_change_handler # Pass the internal handler
                )
                self.sales_items_data_list.append(item_data)
                self.sales_items_map[item_data.unique_id] = item_data
            self.sales_items_data_list.sort(key=lambda x: (x.book_model.game.game_number, x.book_number))
            self.datatable.rows = [item.to_datarow() for item in self.sales_items_data_list]
            self.on_all_items_loaded_callback(self.sales_items_data_list)
        except Exception as e:
            print(f"Error loading active books for sales table: {e}")
            self.datatable.rows = [ft.DataRow(cells=[ft.DataCell(ft.Text(f"Error loading books: {e}", color=ft.Colors.ERROR))])]
        if self.page and self.page.controls: self.page.update()


    def add_or_update_book_for_sale(self, book_model: BookModel, scanned_ticket_str: Optional[str] = None) -> Optional[SalesEntryItemData]:
        if book_model.id is None: return None
        unique_id = f"book-{book_model.id}"
        item_data = self.sales_items_map.get(unique_id)
        is_new_item_to_list = False
        if item_data:
            print(f"SalesTable: Updating item {unique_id} with scan: {scanned_ticket_str if scanned_ticket_str else 'No Ticket Scan'}")
            try: self.sales_items_data_list.remove(item_data) # Remove if present to re-insert at top
            except ValueError: pass # Not in list, perhaps just in map

            item_data.book_model = book_model # Update underlying model
            item_data.db_current_ticket_no = book_model.current_ticket_number
            item_data.game_name = book_model.game.name if book_model.game else item_data.game_name
            item_data.game_price = book_model.game.price if book_model.game else item_data.game_price
            item_data.game_total_tickets = book_model.game.total_tickets if book_model.game else item_data.game_total_tickets
            item_data.ticket_order = book_model.ticket_order

            if scanned_ticket_str: item_data.update_scanned_ticket_number(scanned_ticket_str)
            else: item_data._calculate_sales() # Recalculate if book state might have changed without a scan
        else:
            is_new_item_to_list = True
            print(f"SalesTable: Adding new item {unique_id} with scan: {scanned_ticket_str if scanned_ticket_str else 'No Ticket Scan'}")
            item_data = SalesEntryItemData(book_model=book_model, on_change_callback=self._internal_item_change_handler)
            if scanned_ticket_str: item_data.update_scanned_ticket_number(scanned_ticket_str)
            else: item_data._calculate_sales()
            self.sales_items_map[unique_id] = item_data

        self.sales_items_data_list.insert(0, item_data)
        self.datatable.rows = [item.to_datarow() for item in self.sales_items_data_list]

        if is_new_item_to_list: # If it was truly a new item added to the list structure
            self.on_all_items_loaded_callback(self.sales_items_data_list) # To update main view's book count
        else: # If just an update to an existing item (even if moved to top)
            self.on_item_change_callback(item_data) # To update main view's totals

        if self.page and self.page.controls: self.page.update()
        return item_data

    def update_datarow_for_item(self, unique_item_id: str):
        item_data = self.sales_items_map.get(unique_item_id)
        if not item_data: return
        try:
            idx_in_list = -1
            for i, current_item_data in enumerate(self.sales_items_data_list):
                if current_item_data.unique_id == unique_item_id: idx_in_list = i; break
            if idx_in_list != -1:
                self.datatable.rows[idx_in_list] = item_data.to_datarow()
            else: self.datatable.rows = [item.to_datarow() for item in self.sales_items_data_list]
        except Exception as e:
            print(f"SalesTable: Error updating specific datarow for {unique_item_id}: {e}. Rebuilding all rows.")
            self.datatable.rows = [item.to_datarow() for item in self.sales_items_data_list]
        if self.page and self.page.controls: self.page.update()

    def get_all_data_items(self) -> List[SalesEntryItemData]: return self.sales_items_data_list
    def get_all_items_for_submission(self) -> List[SalesEntryItemData]:
        return [item for item in self.sales_items_data_list if item.is_processed_for_sale or item.all_tickets_sold_confirmed]
    def get_item_by_book_id(self, book_db_id: int) -> Optional[SalesEntryItemData]:
        return self.sales_items_map.get(f"book-{book_db_id}")