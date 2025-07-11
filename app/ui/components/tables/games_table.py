from math import ceil # Keep ceil for direct use if any overrides pagination
from typing import List, Callable, Optional, Type, Any, Dict
import flet as ft
import datetime

from app.constants import REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER
from app.core.exceptions import WidgetError, ValidationError, DatabaseError, GameNotFoundError
from app.core.models import Game
from app.services.game_service import GameService
from app.data.database import get_db_session # For db interactions within actions
from app.ui.components.common.paginated_data_table import PaginatedDataTable # Import base class
from app.ui.components.common.dialog_factory import create_confirmation_dialog, \
    create_form_dialog  # Import dialog factory
from app.ui.components.widgets import NumberDecimalField


class GamesTable(PaginatedDataTable[Game]):
    def __init__(self, page: ft.Page, game_service: GameService,
                 on_data_changed_stats: Optional[Callable[[int, int, int], None]] = None): # Renamed for clarity

        self.game_service = game_service
        self._on_data_changed_stats = on_data_changed_stats
        self.current_action_game: Optional[Game] = None

        column_definitions: List[Dict[str, Any]] = [
            {"key": "id", "label": "ID", "sortable": True, "numeric": False, "searchable": False,
             "display_formatter": lambda val: ft.Text(str(val), size=12.5)},
            {"key": "name", "label": "Game Name", "sortable": True, "numeric": False, "searchable": True,
             "display_formatter": lambda val: ft.Text(str(val), size=12.5, weight=ft.FontWeight.W_500)},
            {"key": "game_number", "label": "Game No.", "sortable": True, "numeric": True, "searchable": True,
             "display_formatter": lambda val: ft.Text(str(val), size=12.5)},
            {"key": "price", "label": "Price ($)", "sortable": True, "numeric": True, "searchable": True, # Price is now in CENTS
             "display_formatter": lambda val_cents: ft.Text(f"{(val_cents / 100.0):.2f}" if val_cents is not None else "0.00", size=12.5),
             "custom_sort_value_getter": lambda game: game.price}, # Sorts by cents
            {"key": "total_tickets", "label": "Tickets", "sortable": True, "numeric": True, "searchable": True,
             "display_formatter": lambda val: ft.Text(str(val), size=12.5)},
            {"key": "calculated_total_value", "label": "Value ($)", "sortable": True, "numeric": True, "searchable": True, # Value is now in CENTS
             "display_formatter": lambda val_cents, item: ft.Text(f"{(item.calculated_total_value / 100.0):.2f}" if item.calculated_total_value is not None else "0.00", size=12.5),
             "custom_sort_value_getter": lambda game: game.calculated_total_value}, # Sorts by cents
            {"key": "default_ticket_order", "label": "Order", "sortable": True, "numeric": False, "searchable": False,
             "display_formatter": lambda val: ft.Text(str(val).capitalize(), size=12.5)},
            {"key": "created_date", "label": "Created (YYYY-MM-DD)", "sortable": True, "numeric": False, "searchable": False,
             "display_formatter": lambda val_date: ft.Text(val_date.strftime("%Y-%m-%d") if val_date else "", size=12.5)},
            {"key": "expired_date", "label": "Expired (YYYY-MM-DD)", "sortable": True, "numeric": False, "searchable": False,
             "display_formatter": self._format_expired_date_cell},
        ]

        super().__init__(
            page=page,
            fetch_all_data_func=self._fetch_games_data,
            column_definitions=column_definitions,
            action_cell_builder=self._build_action_cell,
            rows_per_page=10,
            initial_sort_key="id",
            initial_sort_ascending=True,
        )

    def _fetch_games_data(self, db_session) -> List[Game]:
        return self.game_service.get_all_games(db_session)

    def _format_expired_date_cell(self, expired_date_val: Optional[datetime.datetime], item: Game) -> ft.Control:
        if item.is_expired and expired_date_val:
            return ft.Text(expired_date_val.strftime("%Y-%m-%d"), size=12.5, color=ft.Colors.RED_ACCENT_700)
        elif not item.is_expired:
            return ft.Text("Active", color=ft.Colors.GREEN_700, weight=ft.FontWeight.BOLD, size=12.5)
        return ft.Text("", size=12.5)

    def _build_action_cell(self, game: Game, table_instance: PaginatedDataTable) -> ft.DataCell:
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

    def _filter_and_sort_displayed_data(self, search_term: str = ""):
        super()._filter_and_sort_displayed_data(search_term)
        if self._on_data_changed_stats and self._all_unfiltered_data is not None:
            total_games = len(self._all_unfiltered_data)
            active_games = sum(1 for g in self._all_unfiltered_data if not g.is_expired)
            expired_games = sum(1 for g in self._all_unfiltered_data if g.is_expired)
            self._on_data_changed_stats(total_games, active_games, expired_games)

    def _open_edit_game_dialog(self, game: Game):
        self.current_action_game = game
        can_edit_restricted_fields = False
        try:
            with get_db_session() as db:
                can_edit_restricted_fields = not self.game_service.check_game_had_sales(db, game.id)
        except Exception as e:
            self.show_error_snackbar(f"Error checking game sales status: {e}")
            return

        game_name_field = ft.TextField(label="Game Name", value=game.name, border_radius=8)
        game_number_field = NumberDecimalField(label="Game No.", value=str(game.game_number), is_integer_only=True, border_radius=8)

        # Price field value should be set in DOLLARS for UI editing. Game.price is in CENTS.
        price_dollars_str = f"{(game.price / 100.0):.2f}" if game.price is not None else ""
        price_field = NumberDecimalField(
            label="Price ($)", value=price_dollars_str, is_money_field=True, currency_symbol="$",
            is_integer_only=False, border_radius=8, disabled=not can_edit_restricted_fields
        )
        total_tickets_field = NumberDecimalField(
            label="Total Tickets", value=str(game.total_tickets), is_integer_only=True,
            border_radius=8, disabled=not can_edit_restricted_fields
        )
        ticket_order_options = [ft.dropdown.Option(order, order.capitalize()) for order in [REVERSE_TICKET_ORDER, FORWARD_TICKET_ORDER]]
        ticket_order_dropdown = ft.Dropdown(
            label="Ticket Order", options=ticket_order_options, value=game.default_ticket_order,
            border_radius=8, disabled=not can_edit_restricted_fields
        )
        error_text_edit = ft.Text(visible=False, color=ft.Colors.RED_700)
        restriction_info_text = ft.Text(
            "Price, Total Tickets, and Order cannot be changed because this game has associated sales records.",
            italic=True, size=11, color=ft.Colors.ORANGE_ACCENT_700,
            visible=not can_edit_restricted_fields
        )
        form_column = ft.Column(
            [game_name_field, game_number_field, restriction_info_text, price_field, total_tickets_field, ticket_order_dropdown, error_text_edit],
            tight=True, spacing=15, scroll=ft.ScrollMode.AUTO,
        )

        def _save_edits_handler(e):
            if not self.current_action_game: return
            error_text_edit.value = ""; error_text_edit.visible = False

            name_val = game_name_field.value.strip() if game_name_field.value else None
            game_number_val = game_number_field.get_value_as_int()

            price_dollars_input_val = None # This will be in dollars
            if not price_field.disabled:
                price_dollars_input_val = price_field.get_value_as_float() # Get as float (dollars) for service

            total_tickets_val = None
            if not total_tickets_field.disabled:
                total_tickets_val = total_tickets_field.get_value_as_int()
            order_val = None
            if not ticket_order_dropdown.disabled:
                order_val = ticket_order_dropdown.value

            try:
                if name_val is not None and not name_val: raise ValidationError("Game Name cannot be empty.")
                if game_number_val is not None and game_number_val <= 0: raise ValidationError("Game Number must be a positive integer.")
                # price_dollars_input_val can be None if field is disabled or empty, service handles None.
                # If not None, service will validate if < 0.

                with get_db_session() as db:
                    self.game_service.update_game(
                        db, self.current_action_game.id,
                        name=name_val, game_number=game_number_val,
                        price_dollars=price_dollars_input_val, # Pass dollar value to service
                        total_tickets=total_tickets_val,
                        default_ticket_order=order_val
                    )
                self.close_dialog_and_refresh(self.page.dialog, f"Game '{name_val or self.current_action_game.name}' updated.") # type: ignore
            except (ValidationError, DatabaseError, GameNotFoundError) as ex:
                error_text_edit.value = str(ex.message if hasattr(ex, 'message') else ex); error_text_edit.visible = True
            except Exception as ex_general:
                error_text_edit.value = f"An unexpected error occurred: {ex_general}"; error_text_edit.visible = True
            if self.page: self.page.update()

        edit_dialog = create_form_dialog(
            page=self.page, title_text=f"Edit Game: {game.name}", form_content_column=form_column,
            on_save_callback=_save_edits_handler,
            on_cancel_callback=lambda ev: self.close_dialog_and_refresh(self.page.dialog), # type: ignore
            save_button_text="Save Changes", min_width=450
        )
        self.page.dialog = edit_dialog; self.page.open(self.page.dialog)

    def _confirm_expire_game_dialog(self, game: Game):
        self.current_action_game = game
        dialog_content = ft.Text(f"Are you sure you want to expire game '{game.name}' (Number: {game.game_number})? Make sure all book instances' sales are recorded.")
        confirm_dialog = create_confirmation_dialog(
            title_text="Confirm Expire", title_color=ft.Colors.RED_700, content_control=dialog_content,
            on_confirm=self._handle_expire_confirmed,
            on_cancel=lambda e: self.close_dialog_and_refresh(self.page.dialog), # type: ignore
            confirm_button_text="Expire Game",
            confirm_button_style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE)
        )
        self.page.dialog = confirm_dialog; self.page.open(self.page.dialog)

    def _handle_expire_confirmed(self, e=None):
        if not self.current_action_game: return
        game_to_expire = self.current_action_game; current_dialog = self.page.dialog
        try:
            with get_db_session() as db:
                self.game_service.expire_game(db, game_id=game_to_expire.id)
            self.close_dialog_and_refresh(current_dialog, f"Game '{game_to_expire.name}' expired.")
        except (GameNotFoundError, DatabaseError) as ex: # GameNotFoundError, DatabaseError
            self.show_error_snackbar(str(ex.message if hasattr(ex, 'message') else ex)) # Use .message if available
            self.close_dialog_and_refresh(current_dialog)
        except Exception as ex_general:
            self.show_error_snackbar(f"An unexpected error occurred: {ex_general}")
            self.close_dialog_and_refresh(current_dialog)
        finally: self.current_action_game = None

    def _confirm_reactivate_game_dialog(self, game: Game):
        self.current_action_game = game
        dialog_content = ft.Text(f"Are you sure you want to re-activate game '{game.name}' (Number: {game.game_number})? Associated books may need separate reactivation.")
        confirm_dialog = create_confirmation_dialog(
            title_text="Confirm Reactivate", title_color=ft.Colors.GREEN_700, content_control=dialog_content,
            on_confirm=self._handle_reactivate_confirmed,
            on_cancel=lambda e: self.close_dialog_and_refresh(self.page.dialog), # type: ignore
            confirm_button_text="Reactivate Game",
            confirm_button_style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)
        )
        self.page.dialog = confirm_dialog; self.page.open(self.page.dialog)

    def _handle_reactivate_confirmed(self, e=None):
        if not self.current_action_game: return
        game_to_reactivate = self.current_action_game; current_dialog = self.page.dialog
        try:
            with get_db_session() as db:
                self.game_service.reactivate_game(db, game_id=game_to_reactivate.id)
            self.close_dialog_and_refresh(current_dialog, f"Game '{game_to_reactivate.name}' reactivated.")
        except (GameNotFoundError, DatabaseError) as ex: # GameNotFoundError, DatabaseError
            self.show_error_snackbar(str(ex.message if hasattr(ex, 'message') else ex))
            self.close_dialog_and_refresh(current_dialog)
        except Exception as ex_general:
            self.show_error_snackbar(f"An unexpected error occurred: {ex_general}")
            self.close_dialog_and_refresh(current_dialog)
        finally: self.current_action_game = None