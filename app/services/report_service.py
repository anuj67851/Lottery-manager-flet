import datetime
from typing import List, Optional, Tuple, Dict, Any

from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph
from sqlalchemy.orm import Session

from app.data import crud_reports, crud_games
from app.utils.pdf_generator import PDFGenerator
from app.config import DB_BASE_DIR
from app.core.models import Game, ShiftSubmission, User as UserModel

class ReportService:
    def get_sales_report_data(
            self,
            db: Session,
            start_date: datetime.datetime,
            end_date: datetime.datetime,
            user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        if end_date.hour == 0 and end_date.minute == 0 and end_date.second == 0:
            end_date = end_date.replace(hour=23, minute=59, second=59)

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
    ) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
        """
        Fetches shift submission summaries for reporting.
        Includes drawer_difference (in cents).
        Aggregated totals are in dollars (float).
        """
        from app.services.shift_service import ShiftService
        shift_service = ShiftService()
        shifts: List[ShiftSubmission] = shift_service.get_shifts_for_report(db, start_date, end_date, user_id)

        report_data_list = []
        sum_delta_online_sales_cents = 0
        sum_delta_online_payouts_cents = 0
        sum_delta_instant_payouts_cents = 0
        sum_calculated_drawer_value_cents = 0 # Renamed from net_drop_value
        sum_drawer_difference_cents = 0

        for shift in shifts:
            user_name = shift.user.username if shift.user else "N/A"
            report_data_list.append({
                "submission_datetime": shift.submission_datetime,
                "user_name": user_name,
                "calendar_date": shift.calendar_date,
                "calculated_delta_online_sales": shift.calculated_delta_online_sales, # cents
                "calculated_delta_online_payouts": shift.calculated_delta_online_payouts, # cents
                "calculated_delta_instant_payouts": shift.calculated_delta_instant_payouts, # cents
                "total_tickets_sold_instant": shift.total_tickets_sold_instant, # count
                "total_value_instant": shift.total_value_instant, # dollars
                "calculated_drawer_value": shift.calculated_drawer_value, # cents
                "drawer_difference": shift.drawer_difference, # cents
                "reported_total_online_sales_today": shift.reported_total_online_sales_today, # cents
                "reported_total_online_payouts_today": shift.reported_total_online_payouts_today, # cents
                "reported_total_instant_payouts_today": shift.reported_total_instant_payouts_today, # cents
            })
            sum_delta_online_sales_cents += shift.calculated_delta_online_sales or 0
            sum_delta_online_payouts_cents += shift.calculated_delta_online_payouts or 0
            sum_delta_instant_payouts_cents += shift.calculated_delta_instant_payouts or 0
            sum_calculated_drawer_value_cents += shift.calculated_drawer_value or 0
            sum_drawer_difference_cents += shift.drawer_difference or 0


        # Convert summed cents to dollars for aggregated_totals dict
        aggregated_totals = {
            "sum_delta_online_sales": sum_delta_online_sales_cents / 100.0,
            "sum_delta_online_payouts": sum_delta_online_payouts_cents / 100.0,
            "sum_delta_instant_payouts": sum_delta_instant_payouts_cents / 100.0,
            "sum_calculated_drawer_value": sum_calculated_drawer_value_cents / 100.0, # Renamed
            "sum_drawer_difference": sum_drawer_difference_cents / 100.0,
        }
        return report_data_list, aggregated_totals


    def generate_sales_report_pdf_from_data(
            self,
            detailed_sales_entries_data: List[Dict[str, Any]],
            shifts_summary_data: List[Dict[str, Any]], # Contains drawer_difference in cents
            aggregated_shift_totals: Dict[str, float],
            total_instant_sales_value: float,
            total_instant_tickets_count: int,
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

            pdf_gen.add_section_title("Overall Summary for Period")
            pdf_gen.add_spacer(6)

            # aggregated_shift_totals are already in dollars
            summary_table_data = [
                [Paragraph("<b>Metric</b>", pdf_gen.styles['TableCell']), Paragraph("<b>Total Value</b>", pdf_gen.styles['TableCellRight'])],
                [Paragraph("Total Online Sales:", pdf_gen.styles['TableCell']), Paragraph(f"${aggregated_shift_totals.get('sum_delta_online_sales', 0):.2f}", pdf_gen.styles['TableCellRight'])],
                [Paragraph("Total Online Payouts:", pdf_gen.styles['TableCell']), Paragraph(f"${aggregated_shift_totals.get('sum_delta_online_payouts', 0):.2f}", pdf_gen.styles['TableCellRight'])],
                [Paragraph("Total Instant Game Sales:", pdf_gen.styles['TableCell']), Paragraph(f"${total_instant_sales_value:.2f}", pdf_gen.styles['TableCellRight'])],
                [Paragraph("Total Instant Game Payouts:", pdf_gen.styles['TableCell']), Paragraph(f"${aggregated_shift_totals.get('sum_delta_instant_payouts', 0):.2f}", pdf_gen.styles['TableCellRight'])],
                [Paragraph("<b>Total Calculated Drawer Value (All Shifts):</b>", pdf_gen.styles['SummaryTotal']), Paragraph(f"<b>${aggregated_shift_totals.get('sum_calculated_drawer_value', 0):.2f}</b>", pdf_gen.styles['SummaryTotal'])],
                [Paragraph("<b>Total Drawer Difference (All Shifts):</b>", pdf_gen.styles['SummaryTotal']), Paragraph(f"<b>${aggregated_shift_totals.get('sum_drawer_difference', 0):.2f}</b>", pdf_gen.styles['SummaryTotal'])],
            ]
            page_width, _ = landscape(letter)
            available_width_summary = page_width - 1.0 * inch
            summary_col_widths = [available_width_summary * 0.7, available_width_summary * 0.3]
            pdf_gen.generate_summary_table(summary_table_data, column_widths=summary_col_widths)
            pdf_gen.add_spacer(18)


            if shifts_summary_data:
                pdf_gen.add_section_title("Shift Submission Summaries (Details per Shift)")
                pdf_gen.add_spacer(6)
                shift_column_headers = ["Submission Time", "User", "Cal. Date", "Δ Online Sales", "Δ Online Payouts", "Δ Instant Payouts", "Instant Tkts", "Instant Value", "Calc. Drawer", "Drawer Diff"] # Added Drawer Diff
                available_width_shifts = page_width - 1.0 * inch
                # Adjusted widths to accommodate the new column
                shift_col_widths = [
                    available_width_shifts * 0.13, available_width_shifts * 0.09, available_width_shifts * 0.09, # Submission, User, Cal Date
                    available_width_shifts * 0.09, available_width_shifts * 0.10, available_width_shifts * 0.11, # Online Sales, Online Payouts, Instant Payouts
                    available_width_shifts * 0.07, available_width_shifts * 0.09, # Instant Tkts, Instant Value
                    available_width_shifts * 0.10, available_width_shifts * 0.10, # Calc Drawer, Drawer Diff
                ]
                pdf_gen.generate_shifts_summary_table(shifts_summary_data, shift_column_headers, shift_col_widths)
                pdf_gen.add_spacer(12)
            else:
                pdf_gen.add_section_title("Shift Submission Summaries")
                pdf_gen.story.append(Paragraph("No shift submission data found for this period.", pdf_gen.styles['FilterInfo']))
                pdf_gen.add_spacer(12)

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