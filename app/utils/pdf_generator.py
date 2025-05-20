import datetime
from typing import List, Dict, Any, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT  # Still used for ParagraphStyle, not TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)


class PDFGenerator:
    def __init__(self, file_path: str, page_size=letter, company_name="Your Company", logo_path=None):
        self.file_path = file_path
        self.page_size = page_size
        self.story = []
        self.company_name = company_name
        self.logo_path = logo_path
        self.setup_styles()

    def setup_styles(self):
        self.styles = getSampleStyleSheet()
        try:
            # Ensure you have Roboto fonts or use Helvetica as fallback
            # pdfmetrics.registerFont(TTFont('Roboto', 'Roboto-Regular.ttf'))
            # pdfmetrics.registerFont(TTFont('RobotoBold', 'Roboto-Bold.ttf'))
            # base_font = 'Roboto'; bold_font = 'RobotoBold'
            base_font = 'Helvetica'; bold_font = 'Helvetica-Bold' # Using Helvetica for broader compatibility
        except: base_font = 'Helvetica'; bold_font = 'Helvetica-Bold'

        self.styles.add(ParagraphStyle(name='ReportTitle', fontName=bold_font, fontSize=20, leading=24, alignment=TA_CENTER, spaceAfter=20, textColor=colors.darkblue))
        self.styles.add(ParagraphStyle(name='ReportSubtitle', fontName=base_font, fontSize=14, leading=18, alignment=TA_CENTER, spaceAfter=20, textColor=colors.darkslategray))
        self.styles.add(ParagraphStyle(name='FilterInfo', fontName=base_font, fontSize=10, leading=12, alignment=TA_CENTER, spaceBefore=6, spaceAfter=12, textColor=colors.darkgrey))
        self.styles.add(ParagraphStyle(name='SectionTitle', fontName=bold_font, fontSize=12, leading=14, spaceBefore=6, spaceAfter=6, textColor=colors.darkblue))
        self.styles.add(ParagraphStyle(name='TableHeader', fontName=bold_font, fontSize=8, leading=10, alignment=TA_CENTER, textColor=colors.whitesmoke))
        self.styles.add(ParagraphStyle(name='TableCell', fontName=base_font, fontSize=8, leading=10, alignment=TA_LEFT))
        self.styles.add(ParagraphStyle(name='TableCellRight', fontName=base_font, fontSize=8, leading=10, alignment=TA_RIGHT))
        self.styles.add(ParagraphStyle(name='TableCellCenter', fontName=base_font, fontSize=8, leading=10, alignment=TA_CENTER))
        self.styles.add(ParagraphStyle(name='SummaryTotal', fontName=bold_font, fontSize=9, leading=11, alignment=TA_RIGHT, textColor=colors.darkblue))
        self.styles.add(ParagraphStyle(name='SummaryLabel', fontName=base_font, fontSize=9, leading=11, alignment=TA_LEFT, textColor=colors.black)) # For summary table labels
        self.styles.add(ParagraphStyle(name='SummaryValue', fontName=bold_font, fontSize=9, leading=11, alignment=TA_RIGHT, textColor=colors.black)) # For summary table values

    def build_pdf(self):
        left_margin = right_margin = 0.5 * inch
        top_margin = bottom_margin = 0.5 * inch
        doc_title = self.story[0].text if self.story and isinstance(self.story[0], Paragraph) else "Report"
        doc_title_safe = "".join(c if c.isalnum() else "_" for c in doc_title)
        doc = SimpleDocTemplate(
            self.file_path, pagesize=self.page_size, leftMargin=left_margin, rightMargin=right_margin,
            topMargin=top_margin, bottomMargin=bottom_margin,
            title=f"{doc_title_safe} - {datetime.datetime.now().strftime('%Y-%m-%d')}", author=self.company_name )
        try: doc.build(self.story)
        except Exception as e:
            print(f"Warning: Error occurred during PDF building: {e}")
            # Fallback basic PDF generation
            c = canvas.Canvas(self.file_path, pagesize=self.page_size)
            c.setFont("Helvetica-Bold", 16); c.drawString(left_margin, self.page_size[1] - top_margin - 20, f"Report - {datetime.datetime.now().strftime('%Y-%m-%d')}")
            c.line(left_margin, self.page_size[1] - top_margin - 30, self.page_size[0] - right_margin, self.page_size[1] - top_margin - 30)
            c.setFont("Helvetica", 10); c.drawString(left_margin, self.page_size[1] - top_margin - 50, "PDF generation error occurred.")
            c.drawString(left_margin, self.page_size[1] - top_margin - 65, f"Details: {e}"); c.save()

    def add_title(self, title_text: str): self.story.append(Paragraph(title_text, self.styles['ReportTitle']))
    def add_section_title(self, title_text: str): self.story.append(Paragraph(title_text, self.styles['SectionTitle']))
    def add_filter_info(self, filter_text: str): self.story.append(Paragraph(filter_text, self.styles['FilterInfo']))
    def add_spacer(self, height_points: int = 12): self.story.append(Spacer(1, height_points))

    def generate_summary_table(self, data: List[List[Paragraph]], column_widths: Optional[List[float]] = None):
        """
        Generates a simple two-column table for summary data (Metric, Value).
        Expects data to be a list of rows, where each row is a list of two Paragraph objects.
        """
        if not data:
            self.story.append(Paragraph("No summary data available.", self.styles['FilterInfo']))
            return

        table = Table(data, colWidths=column_widths)
        style = TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            # Style for the last row if it's a "Total Net Drop" to make it stand out
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey if "Net Drop" in data[-1][0].text else None),
            ('TEXTCOLOR', (0, -1), (0, -1), colors.darkblue if "Net Drop" in data[-1][0].text else colors.black),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold' if "Net Drop" in data[-1][0].text else 'Helvetica'),
        ])
        table.setStyle(style)
        self.story.append(KeepTogether(table))


    def generate_shifts_summary_table(self, data: List[Dict[str, Any]], column_headers: List[str], column_widths: Optional[List[float]] = None):
        if not data: self.story.append(Paragraph("No shift submission data available.", self.styles['FilterInfo'])); return
        table_data = [[Paragraph(header, self.styles['TableHeader']) for header in column_headers]]
        totals = {key: 0 for key in ["calculated_delta_online_sales", "calculated_delta_online_payouts", "calculated_delta_instant_payouts", "total_tickets_sold_instant", "total_value_instant", "net_drop_value"]}
        for item in data:
            row = [ Paragraph(item.get('submission_datetime').strftime('%Y-%m-%d %H:%M') if item.get('submission_datetime') else '', self.styles['TableCellCenter']),
                    Paragraph(str(item.get('user_name', '')), self.styles['TableCell']),
                    Paragraph(item.get('calendar_date').strftime('%Y-%m-%d') if item.get('calendar_date') else '', self.styles['TableCellCenter']),
                    Paragraph(f"${item.get('calculated_delta_online_sales', 0)}", self.styles['TableCellRight']),
                    Paragraph(f"${item.get('calculated_delta_online_payouts', 0)}", self.styles['TableCellRight']),
                    Paragraph(f"${item.get('calculated_delta_instant_payouts', 0)}", self.styles['TableCellRight']),
                    Paragraph(str(item.get('total_tickets_sold_instant', 0)), self.styles['TableCellRight']),
                    Paragraph(f"${item.get('total_value_instant', 0)}", self.styles['TableCellRight']),
                    Paragraph(f"${item.get('net_drop_value', 0)}", self.styles['TableCellRight']), ]
            table_data.append(row)
            for key in totals: totals[key] += item.get(key, 0)
        totals_row_text = [Paragraph("<b>Totals (for listed shifts):</b>", self.styles['SummaryTotal']), '', '',
                           Paragraph(f"<b>${totals['calculated_delta_online_sales']}</b>", self.styles['SummaryTotal']),
                           Paragraph(f"<b>${totals['calculated_delta_online_payouts']}</b>", self.styles['SummaryTotal']),
                           Paragraph(f"<b>${totals['calculated_delta_instant_payouts']}</b>", self.styles['SummaryTotal']),
                           Paragraph(f"<b>{totals['total_tickets_sold_instant']}</b>", self.styles['SummaryTotal']),
                           Paragraph(f"<b>${totals['total_value_instant']}</b>", self.styles['SummaryTotal']),
                           Paragraph(f"<b>${totals['net_drop_value']}</b>", self.styles['SummaryTotal']), ]
        table_data.append(totals_row_text) # Renamed from totals_row
        if not column_widths:
            page_w, _ = self.page_size; avail_w = page_w - 1*inch
            num_c = len(column_headers); def_cw = avail_w / num_c if num_c > 0 else 1*inch
            column_widths = [def_cw] * num_c
        table = Table(table_data, colWidths=column_widths, repeatRows=1)
        style = TableStyle([ ('BACKGROUND', (0,0), (-1,0), colors.darkslateblue), ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
                             ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('ALIGN', (0,0), (-1,0), 'CENTER'),
                             ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('LINEBELOW', (0,0), (-1,0), 1, colors.darkblue),
                             ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.aliceblue, colors.lavender]), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                             ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey), ('LINEABOVE', (0,-1), (-1,-1), 1, colors.darkblue),
                             ('SPAN', (0,-1), (2,-1)), ]) # Span for the "Totals" label
        style.add('ALIGN', (1,1), (1,-2), 'LEFT'); style.add('ALIGN', (0,1), (0,-2), 'CENTER'); style.add('ALIGN', (2,1), (2,-2), 'CENTER')
        for i in range(3, len(column_headers)): style.add('ALIGN', (i,1), (i,-1), 'RIGHT')
        table.setStyle(style); self.story.append(KeepTogether(table))

    def generate_sales_report_table(self, data: List[Dict[str, Any]], column_headers_ignored: List[str], column_widths_ignored: Optional[List[float]] = None):
        if not data: self.story.append(Paragraph("No detailed instant game sales entries.", self.styles['FilterInfo'])); return
        self.add_spacer(6)
        actual_headers = ["Date/Time", "User (via Shift)", "Game", "Book #", "Order", "Start #", "End #", "Qty", "Tkt Price", "Total"]
        table_data = [[Paragraph(h, self.styles['TableHeader']) for h in actual_headers]]
        total_qty, total_value = 0, 0
        for item in data:
            dt_str = item.get('sales_entry_creation_date').strftime('%H:%M:%S') if item.get('sales_entry_creation_date') else ''
            user_shift_str = f"{item.get('shift_submission_datetime').strftime('%Y-%m-%d %H:%M') if item.get('shift_submission_datetime') else ''} {item.get('username', '')}".strip()
            book_disp = f"{item.get('game_number_actual', 'GA')}-{item.get('book_number_actual', 'BK')}"
            row = [ Paragraph(dt_str, self.styles['TableCellCenter']), Paragraph(user_shift_str, self.styles['TableCell']),
                    Paragraph(str(item.get('game_name', '')), self.styles['TableCell']), Paragraph(book_disp, self.styles['TableCellCenter']),
                    Paragraph(str(item.get('ticket_order', '')).capitalize(), self.styles['TableCellCenter']),
                    Paragraph(str(item.get('start_number', '')), self.styles['TableCellRight']), Paragraph(str(item.get('end_number', '')), self.styles['TableCellRight']),
                    Paragraph(str(item.get('count', 0)), self.styles['TableCellRight']),
                    Paragraph(f"${item.get('ticket_price_actual', 0):.2f}", self.styles['TableCellRight']),
                    Paragraph(f"${item.get('sales_entry_total_value', 0):.2f}", self.styles['TableCellRight']), ]
            table_data.append(row)
            total_qty += item.get('count', 0); total_value += item.get('sales_entry_total_value', 0)

        qty_idx = actual_headers.index("Qty")
        total_idx = actual_headers.index("Total")
        totals_row_vals = [Paragraph("<b>Totals (for listed entries):</b>", self.styles['SummaryTotal'])] # Updated label
        totals_row_vals.extend([''] * (qty_idx -1) )
        totals_row_vals.append(Paragraph(f"<b>{total_qty}</b>", self.styles['SummaryTotal']))
        totals_row_vals.extend([''] * (total_idx - qty_idx -1) ) # Corrected span for empty cells
        totals_row_vals.append(Paragraph(f"<b>${total_value:.2f}</b>", self.styles['SummaryTotal']))
        table_data.append(totals_row_vals) # Add the totals row

        page_w, _ = self.page_size; avail_w = page_w - 1*inch
        col_widths = [ avail_w * w for w in [0.08, 0.18, 0.15, 0.10, 0.07, 0.07, 0.07, 0.06, 0.10, 0.12] ]

        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        style = TableStyle([ ('BACKGROUND', (0,0), (-1,0), colors.cadetblue), ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
                             ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('ALIGN', (0,0), (-1,0), 'CENTER'),
                             ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('LINEBELOW', (0,0), (-1,0), 1, colors.darkblue),
                             ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.whitesmoke,colors.lightcyan]), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                             ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey), ('LINEABOVE', (0,-1), (-1,-1), 1, colors.darkblue),
                             ('SPAN', (0,-1), (qty_idx -1,-1)), ]) # Span for the "Totals" label

        # MODIFIED SECTION: Using string literals for alignments
        alignments_str = ['CENTER', 'LEFT', 'LEFT', 'CENTER', 'CENTER', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT']
        for i, align_val_str in enumerate(alignments_str):
            # Apply to data rows (from second row (index 1) up to second to last row (index -2))
            style.add('ALIGN', (i,1), (i,-2), align_val_str)

        # Align specific cells in the totals row (index -1) using string literals
        # Ensure qty_idx and total_idx are valid column indices before applying style
        if 0 <= qty_idx < len(actual_headers):
            style.add('ALIGN', (qty_idx,-1), (qty_idx,-1), 'RIGHT')
        if 0 <= total_idx < len(actual_headers):
            style.add('ALIGN', (total_idx,-1), (total_idx,-1), 'RIGHT')
        # END OF MODIFIED SECTION

        table.setStyle(style); self.story.append(KeepTogether(table))

    def generate_book_open_report_table(self, data: List[Dict[str, Any]], column_headers: List[str], column_widths: Optional[List[float]] = None):
        if not data: self.story.append(Paragraph("No open books found.", self.styles['FilterInfo'])); return
        self.story.append(Paragraph("Open Book Details", self.styles['SectionTitle'])); self.add_spacer(6)
        table_data = [[Paragraph(h, self.styles['TableHeader']) for h in column_headers]]
        grand_total_val = 0
        for item in data:
            act_dt = item.get('activate_date').strftime('%Y-%m-%d %H:%M') if item.get('activate_date') else 'N/A'
            row = [ Paragraph(str(item.get('game_name','')), self.styles['TableCell']), Paragraph(str(item.get('game_number','')), self.styles['TableCellCenter']),
                    Paragraph(str(item.get('book_number','')), self.styles['TableCellCenter']), Paragraph(act_dt, self.styles['TableCellCenter']),
                    Paragraph(str(item.get('current_ticket_number','')), self.styles['TableCellRight']), Paragraph(str(item.get('ticket_order','')).capitalize(), self.styles['TableCellCenter']),
                    Paragraph(str(item.get('remaining_tickets',0)), self.styles['TableCellRight']), Paragraph(f"${item.get('game_price_per_ticket',0):.2f}", self.styles['TableCellRight']),
                    Paragraph(f"${item.get('remaining_value',0):.2f}", self.styles['TableCellRight']), ]
            table_data.append(row); grand_total_val += item.get('remaining_value',0)
        totals_row = [Paragraph("<b>Grand Total Rem. Value:</b>", self.styles['SummaryTotal'])] + ['']*(len(column_headers)-2) + [Paragraph(f"<b>${grand_total_val:.2f}</b>", self.styles['SummaryTotal'])]
        table_data.append(totals_row)
        if not column_widths: page_w, _ = self.page_size; avail_w = page_w - 1*inch; num_c = len(column_headers); def_cw = avail_w/num_c if num_c > 0 else 1*inch; column_widths = [def_cw]*num_c
        table = Table(table_data, colWidths=column_widths, repeatRows=1)
        style = TableStyle([('BACKGROUND',(0,0),(-1,0),colors.cornflowerblue),('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('ALIGN',(0,0),(-1,0),'CENTER'),('GRID',(0,0),(-1,-1),0.5,colors.grey),('LINEBELOW',(0,0),(-1,0),1,colors.darkblue),('ROWBACKGROUNDS',(0,1),(-1,-2),[colors.whitesmoke,colors.lightgrey]),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('BACKGROUND',(0,-1),(-1,-1),colors.lightsteelblue),('LINEABOVE',(0,-1),(-1,-1),1,colors.darkblue),('SPAN',(0,-1),(len(column_headers)-2,-1)),('ALIGN',(len(column_headers)-1,-1),(len(column_headers)-1,-1),'RIGHT')])
        num_r_cols = [4,6,7,8]; cen_cols = [1,2,3,5] # These are column indices
        for idx in num_r_cols: style.add('ALIGN',(idx,1),(idx,-2),'RIGHT') # Align data rows
        for idx in cen_cols: style.add('ALIGN',(idx,1),(idx,-2),'CENTER') # Align data rows
        # First column (index 0) will default to TableCell style (TA_LEFT) or need explicit 'LEFT' if default cell style is different
        style.add('ALIGN',(0,1),(0,-2),'LEFT') # Explicitly set first column to LEFT for data rows
        table.setStyle(style); self.story.append(KeepTogether(table))

    def generate_game_expiry_report_table(self, data: List[Dict[str, Any]], column_headers: List[str], column_widths: Optional[List[float]] = None):
        if not data: self.story.append(Paragraph("No games found.", self.styles['FilterInfo'])); return
        self.story.append(Paragraph("Game Expiry Details", self.styles['SectionTitle'])); self.add_spacer(6)
        table_data = [[Paragraph(h, self.styles['TableHeader']) for h in column_headers]]
        for item in data:
            cr_dt = item.get('created_date').strftime('%Y-%m-%d') if item.get('created_date') else 'N/A'
            ex_dt_val = item.get('expired_date'); st_str = "Expired" if item.get('is_expired') else "Active"
            ex_dt_str = ex_dt_val.strftime('%Y-%m-%d') if ex_dt_val else ('-' if st_str=="Active" else 'N/A')
            row = [ Paragraph(str(item.get('name','')), self.styles['TableCell']), Paragraph(str(item.get('game_number','')), self.styles['TableCellCenter']),
                    Paragraph(f"${item.get('price',0):.2f}", self.styles['TableCellRight']), Paragraph(str(item.get('total_tickets',0)), self.styles['TableCellRight']),
                    Paragraph(st_str, self.styles['TableCellCenter']), Paragraph(cr_dt, self.styles['TableCellCenter']), Paragraph(ex_dt_str, self.styles['TableCellCenter']), ]
            table_data.append(row)
        if not column_widths: page_w,_=self.page_size; avail_w=page_w-1*inch; num_c=len(column_headers); def_cw=avail_w/num_c if num_c > 0 else 1*inch; column_widths=[def_cw]*num_c
        table = Table(table_data, colWidths=column_widths, repeatRows=1)
        style = TableStyle([('BACKGROUND',(0,0),(-1,0),colors.cornflowerblue),('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('ALIGN',(0,0),(-1,0),'CENTER'),('GRID',(0,0),(-1,-1),0.5,colors.grey),('LINEBELOW',(0,0),(-1,0),1,colors.darkblue),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.whitesmoke,colors.lightgrey]),('VALIGN',(0,0),(-1,-1),'MIDDLE')])
        num_r_cols = [2,3]; cen_cols = [1,4,5,6] # Column indices
        for idx in num_r_cols: style.add('ALIGN',(idx,1),(idx,-1),'RIGHT') # For all data rows
        for idx in cen_cols: style.add('ALIGN',(idx,1),(idx,-1),'CENTER') # For all data rows
        style.add('ALIGN',(0,1),(0,-1),'LEFT') # Explicitly set first column to LEFT for data rows
        table.setStyle(style); self.story.append(KeepTogether(table))

    def generate_stock_levels_report_table(self, data: List[Dict[str, Any]], column_headers: List[str], column_widths: Optional[List[float]] = None):
        if not data: self.story.append(Paragraph("No stock data found.", self.styles['FilterInfo'])); return
        self.story.append(Paragraph("Stock Level Details", self.styles['SectionTitle'])); self.add_spacer(6)
        table_data = [[Paragraph(h, self.styles['TableHeader']) for h in column_headers]]
        grand_total_val = 0
        for item in data:
            act_val = item.get('active_stock_value',0); grand_total_val += act_val
            row = [ Paragraph(str(item.get('game_name','')), self.styles['TableCell']), Paragraph(str(item.get('game_number','')), self.styles['TableCellCenter']),
                    Paragraph(f"${item.get('game_price_per_ticket',0):.2f}", self.styles['TableCellRight']), Paragraph(str(item.get('total_books',0)), self.styles['TableCellRight']),
                    Paragraph(str(item.get('active_books',0)), self.styles['TableCellRight']), Paragraph(str(item.get('finished_books',0)), self.styles['TableCellRight']),
                    Paragraph(str(item.get('pending_books',0)), self.styles['TableCellRight']), Paragraph(f"${act_val:.2f}", self.styles['TableCellRight']), ]
            table_data.append(row)
        totals_row = [Paragraph("<b>Grand Total Active Stock Value:</b>", self.styles['SummaryTotal'])] + ['']*(len(column_headers)-2) + [Paragraph(f"<b>${grand_total_val:.2f}</b>", self.styles['SummaryTotal'])]
        table_data.append(totals_row)
        if not column_widths: page_w,_=self.page_size; avail_w=page_w-1*inch; num_c=len(column_headers); def_cw=avail_w/num_c if num_c>0 else 1*inch; column_widths=[def_cw]*num_c
        table = Table(table_data, colWidths=column_widths, repeatRows=1)
        style = TableStyle([('BACKGROUND',(0,0),(-1,0),colors.cornflowerblue),('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('ALIGN',(0,0),(-1,0),'CENTER'),('GRID',(0,0),(-1,-1),0.5,colors.grey),('LINEBELOW',(0,0),(-1,0),1,colors.darkblue),('ROWBACKGROUNDS',(0,1),(-1,-2),[colors.whitesmoke,colors.lightgrey]),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('BACKGROUND',(0,-1),(-1,-1),colors.lightsteelblue),('LINEABOVE',(0,-1),(-1,-1),1,colors.darkblue),('SPAN',(0,-1),(len(column_headers)-2,-1)),('ALIGN',(len(column_headers)-1,-1),(len(column_headers)-1,-1),'RIGHT')])
        num_r_cols = [2,3,4,5,6,7]; cen_cols = [1] # Column indices
        for idx in num_r_cols: style.add('ALIGN',(idx,1),(idx,-2),'RIGHT') # Align data rows
        for idx in cen_cols: style.add('ALIGN',(idx,1),(idx,-2),'CENTER') # Align data rows
        style.add('ALIGN',(0,1),(0,-2),'LEFT') # Explicitly set first column to LEFT for data rows
        table.setStyle(style); self.story.append(KeepTogether(table))