# Filename: app\ui\components\tables\games_table.py
from math import expm1, ceil
from typing import List, Callable, Optional, Type, Any
import flet as ft
import datetime

from app.core.exceptions import WidgetError, ValidationError, DatabaseError, GameNotFoundError
from app.core.models import Game
from app.services.game_service import GameService
from app.data.database import get_db_session

class GamesTable(ft.Container):
    def __init__(self, page: ft.Page, game_service: GameService,
                 on_data_changed: Optional[Callable[[int, int, int], None]] = None):
        super().__init__(expand=True, padding=ft.padding.symmetric(horizontal=5))
        self.page = page
        self.game_service = game_service
        self.on_data_changed = on_data_changed

        self.all_games_unfiltered: List[Type[Game]] = []
        self.games: List[Type[Game]] = []

        self.current_sort_column_index: Optional[int] = 0
        self.current_sort_ascending: bool = True

        self.column_keys = [
            "id", "name", "game_number", "price", "total_tickets",
            "calculated_total_value",
            "default_ticket_order", "created_date", "expired_date"
        ]

        self.rows_per_page: int = 10
        self.current_page_number: int = 1
        self._last_search_term: str = ""

        self.datatable = ft.DataTable(
            columns=[],
            rows=[],
            column_spacing=20,
            expand=True,
            vertical_lines=ft.BorderSide(width=0.5, color=ft.Colors.with_opacity(0.15, ft.Colors.ON_SURFACE)), # CORRECTED
            horizontal_lines=ft.BorderSide(width=0.5, color=ft.Colors.with_opacity(0.1, ft.Colors.ON_SURFACE)), # CORRECTED
            sort_ascending=self.current_sort_ascending,
            sort_column_index=self.current_sort_column_index,
            heading_row_height=40,
            data_row_max_height=48,
        )

        self.prev_button = ft.IconButton(
            ft.Icons.KEYBOARD_ARROW_LEFT_ROUNDED, on_click=self._prev_page, tooltip="Previous Page", disabled=True # CORRECTED
        )
        self.next_button = ft.IconButton(
            ft.Icons.KEYBOARD_ARROW_RIGHT_ROUNDED, on_click=self._next_page, tooltip="Next Page", disabled=True # CORRECTED
        )
        self.page_info_text = ft.Text(
            f"Page {self.current_page_number} of 1",
            weight=ft.FontWeight.W_500,
            color=ft.Colors.ON_SURFACE_VARIANT # CORRECTED
        )

        pagination_controls_row = ft.Row(
            [self.prev_button, self.page_info_text, self.next_button],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10
        )

        table_with_pagination_column = ft.Column(
            [
                ft.Container(content=self.datatable, expand=True, padding=ft.padding.only(bottom=10)),
                pagination_controls_row
            ],
            expand=True,
            spacing=5
        )

        self.content = ft.Card(
            content=ft.Container(
                content=table_with_pagination_column,
                padding=15,
                border_radius=8
            ),
            elevation=2,
        )

        self._set_initial_table_columns()
        self.refresh_data()


    def _set_initial_table_columns(self):
        if not self.datatable.columns:
            self.datatable.columns = [
                ft.DataColumn(ft.Text("ID", weight=ft.FontWeight.BOLD, size=13), on_sort=self._handle_column_sort),
                ft.DataColumn(ft.Text("Game Name", weight=ft.FontWeight.BOLD, size=13), on_sort=self._handle_column_sort),
                ft.DataColumn(ft.Text("Game No.", weight=ft.FontWeight.BOLD, size=13), on_sort=self._handle_column_sort, numeric=True),
                ft.DataColumn(ft.Text("Price ($)", weight=ft.FontWeight.BOLD, size=13), on_sort=self._handle_column_sort, numeric=True),
                ft.DataColumn(ft.Text("Tickets", weight=ft.FontWeight.BOLD, size=13), on_sort=self._handle_column_sort, numeric=True),
                ft.DataColumn(ft.Text("Value ($)", weight=ft.FontWeight.BOLD, size=13), on_sort=self._handle_column_sort, numeric=True),
                ft.DataColumn(ft.Text("Order", weight=ft.FontWeight.BOLD, size=13), on_sort=self._handle_column_sort),
                ft.DataColumn(ft.Text("Created", weight=ft.FontWeight.BOLD, size=13), on_sort=self._handle_column_sort),
                ft.DataColumn(ft.Text("Expired", weight=ft.FontWeight.BOLD, size=13), on_sort=self._handle_column_sort),
                ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.BOLD, size=13), numeric=True),
            ]

    def _build_layout(self) -> ft.Column:
        # This method is not strictly necessary if self.content is set in __init__
        # and ft.Container uses it directly.
        # Returning the primary content structure if Flet calls this.
        # For a custom component inheriting ft.Container, self.content is usually the way.
        if isinstance(self.content, ft.Control):
            return ft.Column([self.content], expand=True)
        return ft.Column([ft.Text("Error: Content not initialized properly")], expand=True)


    def refresh_data(self, search_term: str = ""):
        self._last_search_term = search_term
        try:
            with get_db_session() as db:
                self.all_games_unfiltered = self.game_service.get_all_games(db)

            self.current_page_number = 1
            self.filter_and_sort_games(search_term)

            all_games_count_for_stats = len(self.all_games_unfiltered)
            active_in_all = sum(1 for g in self.all_games_unfiltered if not g.is_expired)
            expired_in_all = sum(1 for g in self.all_games_unfiltered if g.is_expired)
            if self.on_data_changed:
                self.on_data_changed(all_games_count_for_stats, active_in_all, expired_in_all)

        except Exception as e:
            print(f"Error refreshing games table data: {e}")
            if self.page:
                error_msg = f"Error loading games: {type(e).__name__}"
                if "Control must be added" in str(e): # This specific error was a concern
                    error_msg = "Error initializing table display. Please try refreshing."
                self.page.open(ft.SnackBar(ft.Text(error_msg), open=True, bgcolor=ft.Colors.ERROR)) # CORRECTED


    def filter_and_sort_games(self, search_term: str = ""):
        search_term_lower = search_term.lower().strip()
        self._last_search_term = search_term

        if not search_term_lower:
            self.games = list(self.all_games_unfiltered)
        else:
            self.games = [
                game for game in self.all_games_unfiltered
                if search_term_lower in str(game.name).lower() or \
                   search_term_lower in str(game.game_number).lower() or \
                   search_term_lower in str(f"{game.price/100:.2f}") or \
                   search_term_lower in str(game.total_tickets).lower() or \
                   search_term_lower in str(f"{(game.price * game.total_tickets)/100:.2f}")
            ]

        if self.current_sort_column_index is not None and self.current_sort_column_index < len(self.column_keys):
            sort_key_attr = self.column_keys[self.current_sort_column_index]

            def get_sort_value(game_obj: Game) -> Any:
                if sort_key_attr == "calculated_total_value":
                    return (game_obj.price * game_obj.total_tickets) if game_obj.price is not None and game_obj.total_tickets is not None else float('-inf')

                val = getattr(game_obj, sort_key_attr, None)

                if sort_key_attr == "price":
                    val = val / 100 if val is not None else None

                if isinstance(val, str):
                    return val.lower()
                if val is None:
                    if self.current_sort_ascending:
                        return datetime.datetime.min if sort_key_attr == "expired_date" else float('-inf')
                    else:
                        return datetime.datetime.max if sort_key_attr == "expired_date" else float('inf')
                return val

            self.games.sort(key=get_sort_value, reverse=not self.current_sort_ascending)

        self._update_datatable()


    def _handle_column_sort(self, e: ft.ControlEvent):
        clicked_column_label_widget = e.control.label
        if not isinstance(clicked_column_label_widget, ft.Text):
            print("Warning: Column label is not a Text widget, cannot determine sort.")
            return
        clicked_column_label = clicked_column_label_widget.value

        idx = -1
        if not self.datatable.columns:
            self._set_initial_table_columns()

        for i, col_def in enumerate(self.datatable.columns): # Use self.datatable.columns here
            if isinstance(col_def.label, ft.Text) and col_def.label.value == clicked_column_label:
                if col_def.on_sort is not None and i < len(self.column_keys):
                    idx = i
                    break

        if idx != -1:
            if self.current_sort_column_index == idx:
                self.current_sort_ascending = not self.current_sort_ascending
            else:
                self.current_sort_column_index = idx
                self.current_sort_ascending = True

            self.datatable.sort_column_index = self.current_sort_column_index
            self.datatable.sort_ascending = self.current_sort_ascending

            self.current_page_number = 1
            self.filter_and_sort_games(self._last_search_term)
        else:
            print(f"Warning: Could not determine sort column index for label: {clicked_column_label}")


    def _update_pagination_controls(self):
        if not self.page_info_text.page:
            # print("Debug: _update_pagination_controls called, but controls not on page yet.")
            return

        total_rows = len(self.games)
        total_pages = ceil(total_rows / self.rows_per_page) if total_rows > 0 else 1

        self.page_info_text.value = f"Page {self.current_page_number} of {total_pages}"
        self.prev_button.disabled = self.current_page_number == 1
        self.next_button.disabled = self.current_page_number == total_pages or total_pages == 0
        # Individual updates removed, relying on page.update() in _update_datatable

    def _prev_page(self, e):
        if self.current_page_number > 1:
            self.current_page_number -= 1
            self._update_datatable()

    def _next_page(self, e):
        total_rows = len(self.games)
        total_pages = ceil(total_rows / self.rows_per_page) if total_rows > 0 else 1
        if self.current_page_number < total_pages:
            self.current_page_number += 1
            self._update_datatable()

    def _update_datatable(self):
        if not self.datatable.columns: # Defensive: ensure columns are set
            self._set_initial_table_columns()

        self.datatable.sort_column_index = self.current_sort_column_index
        self.datatable.sort_ascending = self.current_sort_ascending

        start_index = (self.current_page_number - 1) * self.rows_per_page
        end_index = start_index + self.rows_per_page
        paginated_games = self.games[start_index:end_index]

        rows = []
        for game in paginated_games:
            actions_controls = []
            edit_button = ft.IconButton(
                ft.Icons.EDIT_ROUNDED, tooltip="Edit Game", icon_color=ft.Colors.PRIMARY, # CORRECTED
                icon_size=18, on_click=lambda e, g=game: self._open_edit_game_dialog(g))
            actions_controls.append(edit_button)

            if not game.is_expired:
                expire_button = ft.IconButton(
                    ft.Icons.REMOVE_CIRCLE_OUTLINE_ROUNDED, tooltip="Expire game", icon_color=ft.Colors.RED_ACCENT_700, # CORRECTED
                    icon_size=18, on_click=lambda e, g=game: self._confirm_expire_game_dialog(g))
                actions_controls.append(expire_button)
            else:
                reactivate_button = ft.IconButton(
                    ft.Icons.ADD_CIRCLE_OUTLINE_ROUNDED, tooltip="Reactivate Game", icon_color=ft.Colors.GREEN_ACCENT_700, # CORRECTED
                    icon_size=18, on_click=lambda e, g=game: self._confirm_reactivate_game_dialog(g))
                actions_controls.append(reactivate_button)

            cell_text_size = 12.5

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(game.id), size=cell_text_size)),
                        ft.DataCell(ft.Text(game.name, size=cell_text_size, weight=ft.FontWeight.W_500)),
                        ft.DataCell(ft.Text(str(game.game_number), size=cell_text_size)),
                        ft.DataCell(ft.Text(f"{game.price/100:.2f}", size=cell_text_size)),
                        ft.DataCell(ft.Text(str(game.total_tickets), size=cell_text_size)),
                        ft.DataCell(ft.Text(f"{(game.price * game.total_tickets)/100:.2f}", size=cell_text_size)),
                        ft.DataCell(ft.Text(str(game.default_ticket_order).capitalize(), size=cell_text_size)),
                        ft.DataCell(ft.Text(game.created_date.strftime("%Y-%m-%d"), size=cell_text_size)),
                        ft.DataCell(
                            ft.Text(game.expired_date.strftime("%Y-%m-%d"), size=cell_text_size) if game.expired_date
                            else ft.Text("Active", color=ft.Colors.GREEN_700, weight=ft.FontWeight.BOLD, size=cell_text_size) # CORRECTED
                        ),
                        ft.DataCell(ft.Row(actions_controls, spacing=-5, alignment=ft.MainAxisAlignment.END, vertical_alignment=ft.CrossAxisAlignment.CENTER)),
                    ],
                    color={"hovered": ft.Colors.with_opacity(0.05, ft.Colors.PRIMARY)}, # CORRECTED
                )
            )
        self.datatable.rows = rows

        self._update_pagination_controls()

        if self.page:
            self.page.update()


    def _close_dialog(self, e=None):
        if self.page.dialog:
            self.page.close(self.page.dialog)
            self.page.update()
            self.page.dialog = None

    def _open_edit_game_dialog(self, game: Game):
        self.page.open(ft.SnackBar(ft.Text(f"Edit game {game.name} - (Not Implemented)"), open=True))

    def _confirm_expire_game_dialog(self, game: Game):
        self.current_expire_game = game
        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Expire", color=ft.Colors.RED_700), # CORRECTED
            content=ft.Text(f"Are you sure you want to expire game '{game.name}' (Number: {game.game_number})? Please make sure all the instances values are added to sales entry for the day."),
            actions=[
                ft.TextButton("Cancel", on_click=self._close_dialog),
                ft.FilledButton("Expire Game", style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE), # CORRECTED
                                on_click=self._handle_deactivate_confirmed),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(self.page.dialog)


    def _handle_deactivate_confirmed(self, e=None):
        try:
            with get_db_session() as db:
                self.game_service.expire_game(db, game_id=self.current_expire_game.id)
            self.page.open(ft.SnackBar(ft.Text(f"Game (ID: {self.current_expire_game.id}, Name: {self.current_expire_game.name}, Number: {self.current_expire_game.game_number}) expired successfully."), open=True))
            self._close_dialog()
            self.refresh_data(self._last_search_term)
        except GameNotFoundError as ex:
            self._close_dialog()
            self.page.open(ft.SnackBar(ft.Text(str(ex)), open=True, bgcolor=ft.Colors.ERROR)) # CORRECTED
            self.refresh_data(self._last_search_term)
        except DatabaseError as ex:
            self._close_dialog()
            self.page.open(ft.SnackBar(ft.Text(f"Error expiring game: {ex}"), open=True, bgcolor=ft.Colors.ERROR)) # CORRECTED
        except Exception as ex_general:
            self._close_dialog()
            self.page.open(ft.SnackBar(ft.Text(f"An unexpected error occurred: {ex_general}"), open=True, bgcolor=ft.Colors.ERROR)) # CORRECTED


    def _confirm_reactivate_game_dialog(self, game: Game):
        self.current_reactivate_game = game
        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Reactivate", color=ft.Colors.GREEN_700), # CORRECTED
            content=ft.Text(f"Are you sure you want to re-activate game '{game.name}' (Number: {game.game_number})? You need to re-activate books too if they were previously active before expiration."),
            actions=[
                ft.TextButton("Cancel", on_click=self._close_dialog),
                ft.FilledButton("Reactivate Game", style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE), # CORRECTED
                                on_click=self._handle_reactivate_confirmed),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(self.page.dialog)

    def _handle_reactivate_confirmed(self, e=None):
        try:
            with get_db_session() as db:
                self.game_service.reactivate_game(db, game_id=self.current_reactivate_game.id)
            self.page.open(ft.SnackBar(ft.Text(f"Game (ID: {self.current_reactivate_game.id}, Name: {self.current_reactivate_game.name}, Number: {self.current_reactivate_game.game_number}) re-activated successfully."), open=True))
            self._close_dialog()
            self.refresh_data(self._last_search_term)
        except GameNotFoundError as ex:
            self._close_dialog()
            self.page.open(ft.SnackBar(ft.Text(str(ex)), open=True, bgcolor=ft.Colors.ERROR)) # CORRECTED
            self.refresh_data(self._last_search_term)
        except DatabaseError as ex:
            self._close_dialog()
            self.page.open(ft.SnackBar(ft.Text(f"Error reactivating game: {ex}"), open=True, bgcolor=ft.Colors.ERROR)) # CORRECTED
        except Exception as ex_general:
            self._close_dialog()
            self.page.open(ft.SnackBar(ft.Text(f"An unexpected error occurred: {ex_general}"), open=True, bgcolor=ft.Colors.ERROR)) # CORRECTED