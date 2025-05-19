import datetime
import os
from typing import List, Optional, Tuple, Dict, Any

from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from sqlalchemy.orm import Session

from app.data import crud_reports, crud_games # Added crud_games
from app.utils.pdf_generator import PDFGenerator
from app.config import DB_BASE_DIR # For storing reports
from app.core.models import Game # For type hinting

class ReportService:
    def get_sales_report_data(
            self,
            db: Session,
            start_date: datetime.datetime,
            end_date: datetime.datetime,
            user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetches and structures sales data for the report.
        """
        # Ensure end_date includes the whole day if it's just a date
        if end_date.hour == 0 and end_date.minute == 0 and end_date.second == 0:
            end_date = end_date.replace(hour=23, minute=59, second=59)

        return crud_reports.get_sales_entries_for_report(db, start_date, end_date, user_id)

    def generate_sales_report_pdf_from_data(
            self,
            report_data: List[Dict[str, Any]], # Takes pre-fetched data
            start_date: datetime.datetime,
            end_date: datetime.datetime,
            user_filter_name: str, # Takes pre-fetched user name
            pdf_save_path: str,
    ) -> Tuple[bool, str]: # Returns (success_status, file_path_or_error_message)
        """
        Generates a PDF for the sales report using provided data and save path.
        """
        # Ensure end_date includes the whole day for display if it was adjusted
        display_end_date = end_date
        if not (end_date.hour == 23 and end_date.minute == 59 and end_date.second == 59):
            if end_date.hour == 0 and end_date.minute == 0 and end_date.second == 0:
                display_end_date = end_date.replace(hour=23, minute=59, second=59)

        filter_criteria_text = (
            f"Date Range: {start_date.strftime('%Y-%m-%d')} to {display_end_date.strftime('%Y-%m-%d')} | "
            f"User Filter: {user_filter_name}"
        )

        try:
            # Use landscape page size for more horizontal space
            pdf_gen = PDFGenerator(str(pdf_save_path), page_size=landscape(letter))
            pdf_gen.add_title("Sales Report")
            pdf_gen.add_filter_info(filter_criteria_text)
            pdf_gen.add_spacer(6)

            column_headers = ["Date/Time", "User", "Game", "Book #", "Order", "Start #", "End #", "Qty", "Tkt Price", "Total"]

            page_width, _ = landscape(letter)
            available_width = page_width - 1.0 * inch # Total margin

            # Adjusted relative widths for landscape
            col_widths = [
                available_width * 0.15,  # Date/Time
                available_width * 0.10,  # User
                available_width * 0.18,  # Game
                available_width * 0.07,  # Book #
                available_width * 0.07,  # Order
                available_width * 0.07,  # Start #
                available_width * 0.07,  # End #
                available_width * 0.06,  # Qty
                available_width * 0.08,  # Tkt Price
                available_width * 0.10,  # Total
            ]

            pdf_gen.generate_sales_report_table(report_data, column_headers, col_widths)
            pdf_gen.build_pdf()
            return True, str(pdf_save_path)
        except Exception as e:
            print(f"Error generating PDF: {e}")
            return False, f"Failed to generate PDF: {e}"

    # --- Book Open Report ---
    def get_book_open_report_data(self, db: Session, game_id_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        return crud_reports.get_open_books_report_data(db, game_id_filter)

    def generate_book_open_report_pdf(
            self,
            report_data: List[Dict[str, Any]],
            game_filter_name: str,
            pdf_save_path: str
    ) -> Tuple[bool, str]:
        filter_criteria_text = f"Game Filter: {game_filter_name}"
        try:
            pdf_gen = PDFGenerator(str(pdf_save_path), page_size=landscape(letter))
            pdf_gen.add_title("Open Books Report")
            pdf_gen.add_filter_info(filter_criteria_text)
            pdf_gen.add_spacer(6)

            column_headers = ["Game Name", "Game No", "Book No", "Activated", "Curr. Tkt", "Order", "Rem. Tkts", "Tkt Price", "Rem. Value"]

            page_width, _ = landscape(letter)
            available_width = page_width - 1.0 * inch # Total margin
            col_widths = [
                available_width * 0.20,  # Game Name
                available_width * 0.08,  # Game No
                available_width * 0.08,  # Book No
                available_width * 0.12,  # Activated
                available_width * 0.08,  # Curr. Tkt
                available_width * 0.08,  # Order
                available_width * 0.08,  # Rem. Tkts
                available_width * 0.10,  # Tkt Price
                available_width * 0.12,  # Rem. Value
            ]
            pdf_gen.generate_book_open_report_table(report_data, column_headers, col_widths)
            pdf_gen.build_pdf()
            return True, str(pdf_save_path)
        except Exception as e:
            print(f"Error generating Book Open Report PDF: {e}")
            return False, f"Failed to generate PDF: {e}"

    # --- Game Expiry Report ---
    def get_game_expiry_report_data(
            self,
            db: Session,
            status_filter: Optional[str] = None,
            expired_start_date: Optional[datetime.datetime] = None,
            expired_end_date: Optional[datetime.datetime] = None
    ) -> List[Dict[str, Any]]:
        return crud_reports.get_game_expiry_report_data(db, status_filter, expired_start_date, expired_end_date)

    def generate_game_expiry_report_pdf(
            self,
            report_data: List[Dict[str, Any]],
            filter_criteria_text: str, # Pass combined filter string
            pdf_save_path: str
    ) -> Tuple[bool, str]:
        try:
            pdf_gen = PDFGenerator(str(pdf_save_path), page_size=letter) # Portrait for this one might be okay
            pdf_gen.add_title("Game Expiry Report")
            pdf_gen.add_filter_info(filter_criteria_text)
            pdf_gen.add_spacer(6)

            column_headers = ["Game Name", "Game No", "Price", "Total Tkts", "Status", "Created", "Expired On"]

            page_width, _ = letter
            available_width = page_width - 1.0 * inch # Total margin
            col_widths = [
                available_width * 0.25,  # Game Name
                available_width * 0.10,  # Game No
                available_width * 0.10,  # Price
                available_width * 0.10,  # Total Tkts
                available_width * 0.15,  # Status
                available_width * 0.15,  # Created
                available_width * 0.15,  # Expired On
            ]

            pdf_gen.generate_game_expiry_report_table(report_data, column_headers, col_widths)
            pdf_gen.build_pdf()
            return True, str(pdf_save_path)
        except Exception as e:
            print(f"Error generating Game Expiry Report PDF: {e}")
            return False, f"Failed to generate PDF: {e}"

    # --- Stock Levels Report ---
    def get_stock_levels_report_data(self, db: Session, game_id_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        return crud_reports.get_stock_levels_report_data(db, game_id_filter)

    def generate_stock_levels_report_pdf(
            self,
            report_data: List[Dict[str, Any]],
            game_filter_name: str, # Name of the game if filtered, or "All Games"
            pdf_save_path: str
    ) -> Tuple[bool, str]:
        filter_criteria_text = f"Game Filter: {game_filter_name}"
        try:
            pdf_gen = PDFGenerator(str(pdf_save_path), page_size=landscape(letter))
            pdf_gen.add_title("Stock Levels Report")
            pdf_gen.add_filter_info(filter_criteria_text)
            pdf_gen.add_spacer(6)

            column_headers = ["Game Name", "Game No", "Tkt Price", "Total Books", "Active Books", "Finished Books", "Pending Books", "Active Stock Value"]

            page_width, _ = landscape(letter)
            available_width = page_width - 1.0 * inch
            col_widths = [
                available_width * 0.20,  # Game Name
                available_width * 0.08,  # Game No
                available_width * 0.08,  # Tkt Price
                available_width * 0.10,  # Total Books
                available_width * 0.10,  # Active Books
                available_width * 0.10,  # Finished Books
                available_width * 0.10,  # Pending Books
                available_width * 0.15,  # Active Stock Value
            ]

            pdf_gen.generate_stock_levels_report_table(report_data, column_headers, col_widths)
            pdf_gen.build_pdf()
            return True, str(pdf_save_path)
        except Exception as e:
            print(f"Error generating Stock Levels Report PDF: {e}")
            return False, f"Failed to generate PDF: {e}"

    # Helper to get all games for filter dropdowns in report views
    def get_all_games_for_filter(self, db: Session) -> List[Game]:
        return crud_games.get_all_games_sort_by_expiration_prices(db)