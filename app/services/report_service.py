import datetime
import os
from typing import List, Optional, Tuple, Dict, Any

from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph
from sqlalchemy.orm import Session

from app.data import crud_reports, crud_games
from app.utils.pdf_generator import PDFGenerator
from app.config import DB_BASE_DIR
from app.core.models import Game, ShiftSubmission, User as UserModel # Added ShiftSubmission, UserModel for clarity

class ReportService:
    def get_sales_report_data(
            self,
            db: Session,
            start_date: datetime.datetime, # This is the filter for shift submission date
            end_date: datetime.datetime,   # This is the filter for shift submission date
            user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        if end_date.hour == 0 and end_date.minute == 0 and end_date.second == 0:
            end_date = end_date.replace(hour=23, minute=59, second=59)

        # Pass dates as submission date filters
        return crud_reports.get_sales_entries_for_report(
            db,
            start_submission_date=start_date,
            end_submission_date=end_date,
            user_id=user_id
        )

    def get_shifts_summary_data_for_report(
            self,
            db: Session,
            start_date: datetime.datetime,
            end_date: datetime.datetime,
            user_id: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, float]]: # Updated return type
        """
        Fetches shift submission summaries for reporting.
        Returns a tuple: (list of shift data dicts, dict of aggregated totals).
        """
        from app.services.shift_service import ShiftService # Local import to break potential cycle
        shift_service = ShiftService()
        shifts: List[ShiftSubmission] = shift_service.get_shifts_for_report(db, start_date, end_date, user_id)

        report_data_list = []
        sum_delta_online_sales = 0.0
        sum_delta_online_payouts = 0.0
        sum_delta_instant_payouts = 0.0
        sum_net_drop_value = 0.0
        # sum_total_value_instant will be derived from sales_entries_report_data for consistency with UI

        for shift in shifts:
            user_name = shift.user.username if shift.user else "N/A"
            report_data_list.append({
                "submission_datetime": shift.submission_datetime,
                "user_name": user_name,
                "calendar_date": shift.calendar_date,
                "calculated_delta_online_sales": shift.calculated_delta_online_sales,
                "calculated_delta_online_payouts": shift.calculated_delta_online_payouts,
                "calculated_delta_instant_payouts": shift.calculated_delta_instant_payouts,
                "total_tickets_sold_instant": shift.total_tickets_sold_instant,
                "total_value_instant": shift.total_value_instant,
                "net_drop_value": shift.net_drop_value,
                "reported_total_online_sales_today": shift.reported_total_online_sales_today,
                "reported_total_online_payouts_today": shift.reported_total_online_payouts_today,
                "reported_total_instant_payouts_today": shift.reported_total_instant_payouts_today,
            })
            sum_delta_online_sales += shift.calculated_delta_online_sales or 0
            sum_delta_online_payouts += shift.calculated_delta_online_payouts or 0
            sum_delta_instant_payouts += shift.calculated_delta_instant_payouts or 0
            sum_net_drop_value += shift.net_drop_value or 0

        aggregated_totals = {
            "sum_delta_online_sales": sum_delta_online_sales,
            "sum_delta_online_payouts": sum_delta_online_payouts,
            "sum_delta_instant_payouts": sum_delta_instant_payouts,
            "sum_net_drop_value": sum_net_drop_value,
        }
        return report_data_list, aggregated_totals


    def generate_sales_report_pdf_from_data(
            self,
            detailed_sales_entries_data: List[Dict[str, Any]], # Renamed for clarity
            shifts_summary_data: List[Dict[str, Any]],
            aggregated_shift_totals: Dict[str, float], # New parameter for aggregated totals
            total_instant_sales_value: float, # Sum of detailed_sales_entries_data.sales_entry_total_value
            total_instant_tickets_count: int, # Sum of detailed_sales_entries_data.count
            start_date: datetime.datetime,
            end_date: datetime.datetime,
            user_filter_name: str,
            pdf_save_path: str,
    ) -> Tuple[bool, str]:
        display_end_date = end_date
        if not (end_date.hour == 23 and end_date.minute == 59 and end_date.second == 59):
            if end_date.hour == 0 and end_date.minute == 0 and end_date.second == 0:
                display_end_date = end_date.replace(hour=23, minute=59, second=59)

        filter_criteria_text = (
            f"Date Range: {start_date.strftime('%Y-%m-%d %H:%M')} to {display_end_date.strftime('%Y-%m-%d %H:%M')} | "
            f"User Filter: {user_filter_name}"
        )

        try:
            pdf_gen = PDFGenerator(str(pdf_save_path), page_size=landscape(letter))
            pdf_gen.add_title("Sales & Shift Submission Report")
            pdf_gen.add_filter_info(filter_criteria_text)

            # --- Grand Totals Section ---
            # This section will now be added near the top of the PDF.
            # It uses the aggregated_shift_totals passed in.
            pdf_gen.add_section_title("Overall Summary for Period")
            pdf_gen.add_spacer(6)
            summary_table_data = [
                [Paragraph("<b>Metric</b>", pdf_gen.styles['TableHeader']), Paragraph("<b>Total Value</b>", pdf_gen.styles['TableHeader'])],
                [Paragraph("Total Online Sales:", pdf_gen.styles['TableCell']), Paragraph(f"${aggregated_shift_totals.get('sum_delta_online_sales', 0):.2f}", pdf_gen.styles['TableCellRight'])],
                [Paragraph("Total Online Payouts:", pdf_gen.styles['TableCell']), Paragraph(f"${aggregated_shift_totals.get('sum_delta_online_payouts', 0):.2f}", pdf_gen.styles['TableCellRight'])],
                [Paragraph("Total Instant Game Sales:", pdf_gen.styles['TableCell']), Paragraph(f"${total_instant_sales_value:.2f}", pdf_gen.styles['TableCellRight'])],
                [Paragraph("Total Instant Game Payouts:", pdf_gen.styles['TableCell']), Paragraph(f"${aggregated_shift_totals.get('sum_delta_instant_payouts', 0):.2f}", pdf_gen.styles['TableCellRight'])],
                [Paragraph("<b>Total Net Drop (All Shifts):</b>", pdf_gen.styles['SummaryTotal']), Paragraph(f"<b>${aggregated_shift_totals.get('sum_net_drop_value', 0):.2f}</b>", pdf_gen.styles['SummaryTotal'])],
            ]
            page_width, _ = landscape(letter)
            available_width_summary = page_width - 1.0 * inch
            summary_col_widths = [available_width_summary * 0.7, available_width_summary * 0.3]
            pdf_gen.generate_summary_table(summary_table_data, column_widths=summary_col_widths) # New method in PDFGenerator needed
            pdf_gen.add_spacer(18)


            # --- Section 1: Shift Submission Summaries ---
            if shifts_summary_data:
                pdf_gen.add_section_title("Shift Submission Summaries (Details per Shift)")
                pdf_gen.add_spacer(6)
                shift_column_headers = ["Submission Time", "User", "Cal. Date", "Δ Online Sales", "Δ Online Payouts", "Δ Instant Payouts", "Instant Tkts", "Instant Value", "Net Drop"]
                available_width_shifts = page_width - 1.0 * inch
                shift_col_widths = [
                    available_width_shifts * 0.15, available_width_shifts * 0.10, available_width_shifts * 0.10,
                    available_width_shifts * 0.10, available_width_shifts * 0.12, available_width_shifts * 0.13,
                    available_width_shifts * 0.08, available_width_shifts * 0.10, available_width_shifts * 0.12,
                    ]
                pdf_gen.generate_shifts_summary_table(shifts_summary_data, shift_column_headers, shift_col_widths) # Existing method
                pdf_gen.add_spacer(12)
            else:
                pdf_gen.add_section_title("Shift Submission Summaries")
                pdf_gen.story.append(Paragraph("No shift submission data found for this period.", pdf_gen.styles['FilterInfo']))
                pdf_gen.add_spacer(12)

            # --- Section 2: Detailed Sales Entries (Instant Games) ---
            if detailed_sales_entries_data:
                pdf_gen.add_section_title("Detailed Instant Game Sales Entries (Linked to Shifts)")
                pdf_gen.add_spacer(6)
                sales_column_headers = ["Date/Time", "User (via Shift)", "Game", "Book #", "Order", "Start #", "End #", "Qty", "Tkt Price", "Total"]
                sales_col_widths = [
                    available_width_shifts * 0.15, available_width_shifts * 0.12, available_width_shifts * 0.16,
                    available_width_shifts * 0.07, available_width_shifts * 0.07, available_width_shifts * 0.07,
                    available_width_shifts * 0.07, available_width_shifts * 0.06, available_width_shifts * 0.08,
                    available_width_shifts * 0.10,
                    ]
                # This call uses 'detailed_sales_entries_data' and already calculates its own totals for that table.
                pdf_gen.generate_sales_report_table(detailed_sales_entries_data, sales_column_headers, sales_col_widths)
            else:
                pdf_gen.add_section_title("Detailed Instant Game Sales Entries")
                pdf_gen.story.append(Paragraph("No instant game sales entries found for this period.", pdf_gen.styles['FilterInfo']))

            pdf_gen.build_pdf()
            return True, str(pdf_save_path)
        except Exception as e:
            print(f"Error generating Sales & Shift PDF: {e}")
            return False, f"Failed to generate PDF: {e}"

    # --- Other report methods (Book Open, Game Expiry, Stock Levels) ---
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
            available_width = page_width - 1.0 * inch
            col_widths = [
                available_width * 0.20, available_width * 0.08, available_width * 0.08,
                available_width * 0.12, available_width * 0.08, available_width * 0.08,
                available_width * 0.08, available_width * 0.10, available_width * 0.12,
                ]
            pdf_gen.generate_book_open_report_table(report_data, column_headers, col_widths)
            pdf_gen.build_pdf()
            return True, str(pdf_save_path)
        except Exception as e:
            print(f"Error generating Book Open Report PDF: {e}")
            return False, f"Failed to generate PDF: {e}"

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
            filter_criteria_text: str,
            pdf_save_path: str
    ) -> Tuple[bool, str]:
        try:
            pdf_gen = PDFGenerator(str(pdf_save_path), page_size=letter)
            pdf_gen.add_title("Game Expiry Report")
            pdf_gen.add_filter_info(filter_criteria_text)
            pdf_gen.add_spacer(6)
            column_headers = ["Game Name", "Game No", "Price", "Total Tkts", "Status", "Created", "Expired On"]
            page_width, _ = letter
            available_width = page_width - 1.0 * inch
            col_widths = [
                available_width * 0.25, available_width * 0.10, available_width * 0.10,
                available_width * 0.10, available_width * 0.15, available_width * 0.15,
                available_width * 0.15,
                ]
            pdf_gen.generate_game_expiry_report_table(report_data, column_headers, col_widths)
            pdf_gen.build_pdf()
            return True, str(pdf_save_path)
        except Exception as e:
            print(f"Error generating Game Expiry Report PDF: {e}")
            return False, f"Failed to generate PDF: {e}"

    def get_stock_levels_report_data(self, db: Session, game_id_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        return crud_reports.get_stock_levels_report_data(db, game_id_filter)

    def generate_stock_levels_report_pdf(
            self,
            report_data: List[Dict[str, Any]],
            game_filter_name: str,
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
                available_width * 0.20, available_width * 0.08, available_width * 0.08,
                available_width * 0.10, available_width * 0.10, available_width * 0.10,
                available_width * 0.10, available_width * 0.15,
                ]
            pdf_gen.generate_stock_levels_report_table(report_data, column_headers, col_widths)
            pdf_gen.build_pdf()
            return True, str(pdf_save_path)
        except Exception as e:
            print(f"Error generating Stock Levels Report PDF: {e}")
            return False, f"Failed to generate PDF: {e}"

    def get_all_games_for_filter(self, db: Session) -> List[Game]:
        return crud_games.get_all_games_sort_by_expiration_prices(db)