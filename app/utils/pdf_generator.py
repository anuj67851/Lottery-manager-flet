import datetime
import os
from typing import List, Dict, Any, Optional
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image,
    KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

class PDFGenerator:
    def __init__(self, file_path: str, page_size=letter, company_name="Your Company", logo_path=None):
        self.file_path = file_path
        self.page_size = page_size
        self.story = []
        self.company_name = company_name
        self.logo_path = logo_path

        # Initialize styles
        self.setup_styles()

    def setup_styles(self):
        """Setup styles for the document"""
        self.styles = getSampleStyleSheet()

        # Try to register some nicer fonts if available
        try:
            # You may need to replace these with fonts available on your system
            # or remove if not needed
            pdfmetrics.registerFont(TTFont('Roboto', 'Roboto-Regular.ttf'))
            pdfmetrics.registerFont(TTFont('RobotoBold', 'Roboto-Bold.ttf'))
            base_font = 'Roboto'
            bold_font = 'RobotoBold'
        except:
            # Fallback to standard fonts
            base_font = 'Helvetica'
            bold_font = 'Helvetica-Bold'

        # Custom styles with enhanced appearance
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            fontName=bold_font,
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            spaceAfter=20,
            textColor=colors.darkblue
        ))

        self.styles.add(ParagraphStyle(
            name='ReportSubtitle',
            fontName=base_font,
            fontSize=14,
            leading=18,
            alignment=TA_CENTER,
            spaceAfter=20,
            textColor=colors.darkslategray
        ))

        self.styles.add(ParagraphStyle(
            name='FilterInfo',
            fontName=base_font,
            fontSize=10,
            leading=12,
            alignment=TA_CENTER,
            spaceBefore=6,
            spaceAfter=12,
            textColor=colors.darkgrey
        ))

        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            fontName=bold_font,
            fontSize=12,
            leading=14,
            spaceBefore=6,
            spaceAfter=6,
            textColor=colors.darkblue
        ))

        self.styles.add(ParagraphStyle(
            name='TableHeader',
            fontName=bold_font,
            fontSize=9,
            leading=11,
            alignment=TA_CENTER,
            textColor=colors.whitesmoke
        ))

        self.styles.add(ParagraphStyle(
            name='TableCell',
            fontName=base_font,
            fontSize=9,
            leading=11,
            alignment=TA_LEFT
        ))

        self.styles.add(ParagraphStyle(
            name='TableCellRight',
            fontName=base_font,
            fontSize=9,
            leading=11,
            alignment=TA_RIGHT
        ))

        self.styles.add(ParagraphStyle(
            name='SummaryTotal',
            fontName=bold_font,
            fontSize=10,
            leading=12,
            alignment=TA_RIGHT,
            textColor=colors.darkblue
        ))

    def build_pdf(self):
        """Build the PDF using SimpleDocTemplate without callbacks"""
        # Margins
        left_margin = right_margin = 0.75 * inch  # Slightly wider margins
        top_margin = bottom_margin = 0.75 * inch

        # Create document
        doc = SimpleDocTemplate(
            self.file_path,
            pagesize=self.page_size,
            leftMargin=left_margin,
            rightMargin=right_margin,
            topMargin=top_margin,
            bottomMargin=bottom_margin,
            title=f"Sales Report - {datetime.datetime.now().strftime('%Y-%m-%d')}",
            author=self.company_name
        )

        # Try a simple build without page callbacks
        try:
            doc.build(self.story)
        except Exception as e:
            # If build with SimpleDocTemplate fails, try the most minimal approach
            print(f"Warning: Error occurred during PDF building: {e}")
            print("Attempting alternative build method...")

            # Create a canvas directly
            c = canvas.Canvas(self.file_path, pagesize=self.page_size)

            # Add a simple title
            c.setFont("Helvetica-Bold", 16)
            c.drawString(left_margin, self.page_size[1] - top_margin - 20,
                         f"Sales Report - {datetime.datetime.now().strftime('%Y-%m-%d')}")

            # Add a line
            c.line(left_margin, self.page_size[1] - top_margin - 30,
                   self.page_size[0] - right_margin, self.page_size[1] - top_margin - 30)

            # Add text about error
            c.setFont("Helvetica", 10)
            c.drawString(left_margin, self.page_size[1] - top_margin - 50,
                         "PDF generation error occurred.")
            c.drawString(left_margin, self.page_size[1] - top_margin - 65,
                         "Please check the data and try again.")

            # Save the canvas
            c.save()

    def add_header(self, title_text: str, subtitle_text: str = None):
        """Add a beautiful header with optional logo"""
        # Add logo if available
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                # Constrain logo size
                logo = Image(self.logo_path)
                logo.drawHeight = 0.75 * inch
                logo.drawWidth = 0.75 * inch
                self.story.append(logo)
            except Exception:
                # Skip logo if there's an issue
                pass

        # Add title
        self.story.append(Paragraph(title_text, self.styles['ReportTitle']))

        # Add subtitle if provided
        if subtitle_text:
            self.story.append(Paragraph(subtitle_text, self.styles['ReportSubtitle']))

        # Add date
        date_text = f"Generated on {datetime.datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
        self.story.append(Paragraph(date_text, self.styles['FilterInfo']))

        # Add a separator
        self.story.append(HRFlowable(
            width="100%",
            thickness=1,
            color=colors.darkblue,
            spaceBefore=10,
            spaceAfter=20
        ))

    def add_title(self, title_text: str):
        """Add a title (for backward compatibility)"""
        self.story.append(Paragraph(title_text, self.styles['ReportTitle']))

    def add_section_title(self, title_text: str):
        """Add a section title"""
        self.story.append(Paragraph(title_text, self.styles['SectionTitle']))

    def add_filter_info(self, filter_text: str):
        """Add filter information"""
        self.story.append(Paragraph(filter_text, self.styles['FilterInfo']))

    def add_spacer(self, height_points: int = 12):
        """Add vertical space"""
        self.story.append(Spacer(1, height_points))

    def add_page_break(self):
        """Add a page break"""
        self.story.append(PageBreak())

    def add_separator(self, width="100%", color=colors.lightgrey, spaceBefore=10, spaceAfter=10):
        """Add a horizontal separator line"""
        self.story.append(HRFlowable(
            width=width,
            thickness=1,
            color=color,
            spaceBefore=spaceBefore,
            spaceAfter=spaceAfter
        ))

    def generate_sales_report_table(self, data: List[Dict[str, Any]], column_headers: List[str], column_widths: Optional[List[float]] = None):
        """Generate a beautifully styled sales report table"""
        if not data:
            self.story.append(Paragraph("No data available for the selected criteria.", self.styles['FilterInfo']))
            return

        # Add a section title
        self.story.append(Paragraph("Sales Details", self.styles['SectionTitle']))
        self.add_spacer(6)

        # Prepare table data
        table_data = [[Paragraph(header, self.styles['TableHeader']) for header in column_headers]]

        # Add rows
        for item in data:
            date_str = item.get('date').strftime('%Y-%m-%d %H:%M') if item.get('date') else ''
            row = [
                Paragraph(date_str, self.styles['TableCell']),
                Paragraph(str(item.get('username', '')), self.styles['TableCell']),
                Paragraph(str(item.get('game_name', '')), self.styles['TableCell']),
                Paragraph(str(item.get('book_number', '')), self.styles['TableCellRight']),
                Paragraph(str(item.get('ticket_order', '')).capitalize(), self.styles['TableCell']),
                Paragraph(str(item.get('start_number', '')), self.styles['TableCellRight']),
                Paragraph(str(item.get('end_number', '')), self.styles['TableCellRight']),
                Paragraph(str(item.get('count', '')), self.styles['TableCellRight']),
                Paragraph(f"${item.get('game_price', 0):.2f}", self.styles['TableCellRight']),
                Paragraph(f"${item.get('price', 0):.2f}", self.styles['TableCellRight']),
            ]
            table_data.append(row)

        # Calculate totals
        total_tickets = sum(item.get('count', 0) for item in data)
        total_sales = sum(item.get('price', 0) for item in data)

        # Format totals row
        totals = [Paragraph("<b>Totals:</b>", self.styles['SummaryTotal'])] + [''] * 6 + [
            Paragraph(f"<b>{total_tickets}</b>", self.styles['SummaryTotal']),
            '',
            Paragraph(f"<b>${total_sales:.2f}</b>", self.styles['SummaryTotal'])
        ]
        table_data.append(totals)

        # Set default column widths if not provided
        if not column_widths:
            column_widths = [1.2*inch, 1.2*inch, 1.2*inch, 0.6*inch,
                             0.8*inch, 0.6*inch, 0.6*inch, 0.6*inch,
                             0.7*inch, 0.7*inch]

        # Create table
        table = Table(table_data, colWidths=column_widths, repeatRows=1)

        # Define beautiful table style
        style = TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.cornflowerblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),

            # Grid styling
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.darkblue),

            # Row styling
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.whitesmoke, colors.lightgrey]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),

            # Total row styling
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightsteelblue),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.darkblue),
            ('SPAN', (0, -1), (6, -1)),
        ])

        # Align numeric columns to the right
        for idx in [3, 5, 6, 7, 8, 9]:
            style.add('ALIGN', (idx, 1), (idx, -1), 'RIGHT')

        table.setStyle(style)

        # Add table to story
        self.story.append(KeepTogether(table))

        # Add a summary section
        self.add_spacer(15)
        self.story.append(Paragraph("Summary", self.styles['SectionTitle']))
        self.add_spacer(6)

        # Create a summary table
        summary_data = [
            ["Total Tickets Sold", f"{total_tickets}"],
            ["Total Sales Amount", f"${total_sales:.2f}"],
            ["Average Price per Ticket", f"${(total_sales/total_tickets if total_tickets else 0):.2f}"]
        ]

        summary_table = Table(summary_data, colWidths=[3*inch, 1.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightsteelblue),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.darkblue),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))

        self.story.append(summary_table)