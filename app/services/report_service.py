import datetime
import os
from typing import List, Optional, Tuple, Dict, Any

from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from sqlalchemy.orm import Session

from app.data import crud_reports, crud_users
from app.utils.pdf_generator import PDFGenerator
from app.config import DB_BASE_DIR # For storing reports

REPORTS_DIR = DB_BASE_DIR.joinpath("generated_reports")
os.makedirs(REPORTS_DIR, exist_ok=True) # Ensure reports directory exists

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