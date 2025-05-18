from math import expm1
from typing import List, Callable, Optional, Type
import flet as ft

from app.core.exceptions import WidgetError, ValidationError, DatabaseError, GameNotFoundError
from app.core.models import Game
from app.services.game_service import GameService
from app.data.database import get_db_session

class GamesTable(ft.Container):
    def __init__(self, page: ft.Page, game_service: GameService,
                 on_data_changed: Optional[Callable[[int, int, int], None]] = None):
        super().__init__(expand=True, padding=ft.padding.symmetric(horizontal=10))
        self.page = page
        self.game_service = game_service
        self.on_data_changed = on_data_changed # Callback to notify parent of changes

        self.games: List[Type[Game]] = []
        self.datatable = ft.DataTable(
            columns=[], # Will be set in _build_layout
            rows=[],    # Will be set in _build_layout
            column_spacing=25,
            expand=True,
            vertical_lines=ft.BorderSide(width=1, color=ft.Colors.with_opacity(0.2, ft.Colors.ON_SURFACE)),
        )
        self.content = self._build_layout()
        self.refresh_data() # Load initial data

    def _build_layout(self) -> ft.Column:
        return ft.Column(
            controls=[
                self.datatable
            ],
            expand=True,
        )

    def refresh_data(self):
        try:
            total_games = 0
            active_games = 0
            expired_games = 0

            with get_db_session() as db:
                self.games = self.game_service.get_all_games(db)
                total_games = len(self.games)
                for game in self.games:
                    if game.is_expired:
                        expired_games += 1
                    else:
                        active_games += 1

            self._update_datatable()
            if self.on_data_changed:
                self.on_data_changed(total_games, active_games, expired_games)
        except Exception as e:
            print(f"Error refreshing games table data: {e}")
            if self.page:
                self.page.open(ft.SnackBar(ft.Text(f"Error loading games: {e}"), open=True, bgcolor=ft.Colors.ERROR))


    def _update_datatable(self):
        self.datatable.columns = [
            ft.DataColumn(ft.Text("ID", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Game Name", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Game Number", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Price ($)", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Total Tickets", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Default Ticket Order", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Created Date", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Expired Date", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.BOLD), numeric=True), # Align actions to the right
        ]

        rows = []
        for game in self.games:
            actions_controls = []

            edit_button = ft.IconButton(
                icon=ft.Icons.EDIT_ROUNDED,
                tooltip="Edit Game",
                icon_color=ft.Colors.PRIMARY,
                on_click=lambda e, g=game: self._open_edit_game_dialog(g)
            )
            actions_controls.append(edit_button)

            if not game.is_expired:
                expire_button = ft.IconButton(
                    icon=ft.Icons.REMOVE_CIRCLE_OUTLINE_ROUNDED,
                    tooltip="Expire game",
                    icon_color=ft.Colors.RED_ACCENT_700,
                    on_click=lambda e, g=game: self._confirm_expire_game_dialog(g)
                )
                actions_controls.append(expire_button)
            else:
                reactivate_button = ft.IconButton(
                    icon=ft.Icons.ADD_CIRCLE_OUTLINE_ROUNDED,
                    tooltip="Reactivate Game",
                    icon_color=ft.Colors.GREEN_ACCENT_700,
                    on_click=lambda e, g=game: self._confirm_reactivate_game_dialog(g),
                )
                actions_controls.append(reactivate_button)

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(game.id))),
                        ft.DataCell(ft.Text(game.name)),
                        ft.DataCell(ft.Text(str(game.game_number))),
                        ft.DataCell(ft.Text(str(game.price))),
                        ft.DataCell(ft.Text(str(game.total_tickets))),
                        ft.DataCell(ft.Text(str(game.default_ticket_order))),
                        ft.DataCell(ft.Text(game.created_date.strftime("%Y-%m-%d %H:%M"))),
                        ft.DataCell(ft.Text(game.expired_date.strftime("%Y-%m-%d %H:%M")) if game.expired_date else ft.Text("Active")),
                        ft.DataCell(ft.Row(actions_controls, spacing=0, alignment=ft.MainAxisAlignment.END)),
                    ]
                )
            )
        self.datatable.rows = rows
        if self.page: # Ensure table updates if it's already on page
            self.page.update()


    def _close_dialog(self, e=None):
        if self.page.dialog:
            self.page.close(self.page.dialog)
            self.page.dialog = None # Clear dialog from page state
            self.page.update()

    def _open_edit_game_dialog(self, game: Game):
        pass


    def _confirm_expire_game_dialog(self, game: Game):
        self.current_expire_game = game # Store ID for deactivation

        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Expire", color=ft.Colors.RED_700),
            content=ft.Text(f"Are you sure you want to expire game '{game.name}' (Number: {game.game_number})? Please make sure all the instances values are added to sales entry for the day."),
            actions=[
                ft.TextButton("Cancel", on_click=self._close_dialog),
                ft.FilledButton("Expire Game", style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE),
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
            self.refresh_data() # Refresh table
        except GameNotFoundError as ex:
            self._close_dialog() # Close confirmation dialog
            self.page.open(ft.SnackBar(ft.Text(str(ex)), open=True, bgcolor=ft.Colors.ERROR))
            self.refresh_data()
        except DatabaseError as ex:
            self._close_dialog()
            self.page.open(ft.SnackBar(ft.Text(f"Error expiring game: {ex}"), open=True, bgcolor=ft.Colors.ERROR))
        except Exception as ex_general:
            self._close_dialog()
            self.page.open(ft.SnackBar(ft.Text(f"An unexpected error occurred: {ex_general}"), open=True, bgcolor=ft.Colors.ERROR))

    def _confirm_reactivate_game_dialog(self, game: Game):
        self.current_reactivate_game = game # Store game for reactivation

        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Reactivate", color=ft.Colors.GREEN_700),
            content=ft.Text(f"Are you sure you want to re-activate game '{game.name}' (Number: {game.game_number})? You need to re-activate books too if they were previously active before expiration."),
            actions=[
                ft.TextButton("Cancel", on_click=self._close_dialog),
                ft.FilledButton("Reactivate Game", style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
                                on_click=self._handle_reactivate_confirmed),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(self.page.dialog)

    def _handle_reactivate_confirmed(self, e=None):
        try:
            with get_db_session() as db:
                self.game_service.reactivate_game(db, game_id=self.current_reactivate_game.id)
            self.page.open(ft.SnackBar(ft.Text(f"Game (ID: {self.current_expire_game.id}, Name: {self.current_expire_game.name}, Number: {self.current_expire_game.game_number}) re-activated successfully."), open=True))
            self._close_dialog()
            self.refresh_data() # Refresh table
        except GameNotFoundError as ex:
            self._close_dialog() # Close confirmation dialog
            self.page.open(ft.SnackBar(ft.Text(str(ex)), open=True, bgcolor=ft.Colors.ERROR))
            self.refresh_data()
        except DatabaseError as ex:
            self._close_dialog()
            self.page.open(ft.SnackBar(ft.Text(f"Error reactivating game: {ex}"), open=True, bgcolor=ft.Colors.ERROR))
        except Exception as ex_general:
            self._close_dialog()
            self.page.open(ft.SnackBar(ft.Text(f"An unexpected error occurred: {ex_general}"), open=True, bgcolor=ft.Colors.ERROR))
