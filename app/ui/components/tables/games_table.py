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
             "display_formatter": lambda val: ft.Text(f"{val}", size=12.5),
             "custom_sort_value_getter": lambda game: game.price}, # Sort by cents
            {"key": "total_tickets", "label": "Tickets", "sortable": True, "numeric": True, "searchable": True,
             "display_formatter": lambda val: ft.Text(str(val), size=12.5)},
            {"key": "calculated_total_value", "label": "Value ($)", "sortable": True, "numeric": True, "searchable": True,
             "display_formatter": lambda val, item: ft.Text(f"{item.calculated_total_value}", size=12.5),
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