"""Draws the report content as PDFs that look like the paper HACCP tables.

Table 9 is portrait with four weeks across the page and rotated unit names.
Tables 10 and 11 are landscape with a row per day and grey bands.
"""

from io import BytesIO
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape, portrait
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

COMPANY = 'Achieve Cafe Provisions'
HACCP_PLAN = 'HACCP Plan 1.6'  # update when the HACCP plan version changes

INK = colors.black
RED = colors.HexColor('#b4233c')
BAND = colors.HexColor('#e9e9e9')       # the grey bands on Tables 10 and 11
DATE_ROW = colors.HexColor('#f3f3f3')   # the date rows on Table 9
LEGENDS = {
    'storage': '* = out of limit',
    'receiving': '* = out of limit or packaging not OK      - = no delivery      (pkg) = packaging not OK',
    'dispatch': '* = out of limit',
}

STYLES = getSampleStyleSheet()
HEADING = ParagraphStyle('Heading', parent=STYLES['Heading2'], fontName='Helvetica-Bold', fontSize=12, spaceAfter=4)
SMALL = ParagraphStyle('Small', parent=STYLES['Normal'], fontSize=7.5, leading=9, alignment=1, splitLongWords=0)
CELL = ParagraphStyle('Cell', parent=STYLES['Normal'], fontSize=8, leading=10)
NOTE = ParagraphStyle('Note', parent=STYLES['Normal'], fontSize=8, textColor=colors.HexColor('#444444'))


class RotatedText(Flowable):
    """Text turned to read upwards, for the narrow unit columns of Table 9."""

    def __init__(self, text, size=8):
        super().__init__()
        self.text, self.size = text, size

    def wrap(self, available_width, available_height):
        self.width, self.height = self.size + 2, stringWidth(self.text, 'Helvetica-Bold', self.size) + 4
        return self.width, self.height

    def draw(self):
        self.canv.saveState()
        self.canv.setFont('Helvetica-Bold', self.size)
        self.canv.translate(self.size, 2)
        self.canv.rotate(90)
        self.canv.drawString(0, 0, self.text)
        self.canv.restoreState()


def date_text(day):
    return f'{day:%d/%m/%Y}' if day else ''


def red_stars(data, style, first_row, first_column=1):
    """Marks every cell ending in * in red bold, so out-of-limit readings stand out."""
    for r, row in enumerate(data):
        for c, cell in enumerate(row):
            if r >= first_row and c >= first_column and isinstance(cell, str) and cell.endswith('*'):
                style += [('TEXTCOLOR', (c, r), (c, r), RED), ('FONTNAME', (c, r), (c, r), 'Helvetica-Bold')]


def storage_table(sheet, width):
    """Table 9: a label column, then four weeks of one column per unit."""
    unit_count = len(sheet['units'])
    label_width = 28 * mm
    column_width = (width - label_width) / (4 * unit_count)
    total_columns = 1 + 4 * unit_count

    top = [''] + [f'Week {w + 1}' if sheet['weeks'][w] else '' for w in range(4) for _ in range(unit_count)]
    top = [top[0]] + [text if i % unit_count == 0 else '' for i, text in enumerate(top[1:])]
    names = [''] + [RotatedText(name) for _ in range(4) for name in sheet['units']]
    data = [top, names]

    style = [
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.7, INK),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
    ]
    for week in range(4):
        first = 1 + week * unit_count
        style.append(('SPAN', (first, 0), (first + unit_count - 1, 0)))

    for row in sheet['rows']:
        row_number = len(data)
        if row['kind'] == 'date':
            cells = [row['label']]
            for week_date in row['dates']:
                cells += [date_text(week_date)] + [''] * (unit_count - 1)
            for week in range(4):
                first = 1 + week * unit_count
                style.append(('SPAN', (first, row_number), (first + unit_count - 1, row_number)))
            style += [
                ('BACKGROUND', (0, row_number), (-1, row_number), DATE_ROW),
                ('FONTNAME', (0, row_number), (-1, row_number), 'Helvetica-Bold'),
                ('ALIGN', (0, row_number), (0, row_number), 'LEFT'),
            ]
        else:
            cells = [row['label']] + [text for week_cells in row['cells'] for text in week_cells]
            style.append(('ALIGN', (0, row_number), (0, row_number), 'LEFT'))
        data.append(cells)

    red_stars(data, style, first_row=2)
    # Heavier line between weeks, like the paper sheet.
    style += [('LINEBEFORE', (1 + week * unit_count, 0), (1 + week * unit_count, -1), 1.5, INK) for week in range(4)]

    row_heights = [7 * mm, 24 * mm] + [6.2 * mm] * (len(data) - 2)
    table = Table(data, colWidths=[label_width] + [column_width] * (total_columns - 1), rowHeights=row_heights)
    table.setStyle(TableStyle(style))
    return table


def weekly_table(grid, width):
    """Tables 10 and 11: Day, Date, then a column per supplier or run, a row per day, grey bands."""
    day_width, date_width = 26 * mm, 24 * mm
    column_count = max(len(grid['columns']), 1)
    column_width = min((width - day_width - date_width) / column_count, 30 * mm)

    data = [['Day', 'Date'] + [Paragraph(f'<b>{name}</b>', SMALL) for name in grid['columns']]]
    style = [
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.7, INK),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (1, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
    ]
    for index, row in enumerate(grid['rows'], start=1):
        data.append([row['day'], date_text(row['date']), *row['cells']])
        style.append(('BACKGROUND', (0, index), (-1, index), BAND if index % 2 == 0 else colors.white))
        if row['new_week'] and index > 1:
            style.append(('LINEABOVE', (0, index), (-1, index), 1.5, INK))
    red_stars(data, style, first_row=1, first_column=2)

    # Compact rows so four weeks (24 rows) fit on one landscape page, like the paper sheet.
    row_heights = [11 * mm] + [5.7 * mm] * (len(data) - 1)
    table = Table(
        data, colWidths=[day_width, date_width] + [column_width] * column_count, rowHeights=row_heights, repeatRows=1
    )
    table.setStyle(TableStyle(style))
    return table


def corrective_table(corrective, width):
    # Paragraphs wrap long notes inside their cell instead of running into the next column.
    rows = [[Paragraph(escape(text), CELL) for text in row] for row in corrective['rows']]
    data = [corrective['headers'], *rows]
    table = Table(data, repeatRows=1, colWidths=[width * 0.17, width * 0.17, width * 0.32, width * 0.16, width * 0.18])
    table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, INK),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), BAND),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return table


def corrective_section(corrective, width):
    story = [Spacer(1, 6 * mm), Paragraph('<b>Corrective actions</b>', STYLES['Heading4'])]
    if corrective['rows']:
        story.append(corrective_table(corrective, width))
    else:
        story.append(Paragraph('None in this period.', NOTE))
    return story


def page_furniture(period):
    """The running header and footer, like the paper pages."""
    def draw(canvas, document):
        width, height = document.pagesize
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        canvas.drawString(document.leftMargin, height - 9 * mm, COMPANY)
        canvas.drawCentredString(width / 2, height - 9 * mm, HACCP_PLAN)
        canvas.drawRightString(width - document.rightMargin, height - 9 * mm, period)
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.grey)
        canvas.drawString(document.leftMargin, 7 * mm, f'Generated {timezone.localtime():%d/%m/%Y %I:%M %p}')
        canvas.drawRightString(width - document.rightMargin, 7 * mm, f'Page {document.page}')
        canvas.restoreState()
    return draw


def render_report(kind, heading, start, end, content, corrective):
    """The finished PDF as bytes. `content` comes from grids.REPORTS for this kind."""
    pagesize = portrait(A4) if kind == 'storage' else landscape(A4)
    document = SimpleDocTemplate(
        BytesIO(), pagesize=pagesize, leftMargin=10 * mm, rightMargin=10 * mm, topMargin=16 * mm, bottomMargin=14 * mm,
        title=f'{COMPANY} - {heading}',
    )
    width = pagesize[0] - document.leftMargin - document.rightMargin
    title = Paragraph(heading.replace('&', '&amp;'), HEADING)

    story = []
    if kind == 'storage':
        for number, sheet in enumerate(content):
            story += [title, storage_table(sheet, width), Spacer(1, 3 * mm), Paragraph(LEGENDS[kind], NOTE)]
            if number == len(content) - 1:
                story += corrective_section(corrective, width)
            else:
                story.append(PageBreak())
    else:
        story += [title, weekly_table(content, width), Spacer(1, 3 * mm), Paragraph(LEGENDS[kind], NOTE)]
        story += corrective_section(corrective, width)

    buffer = BytesIO()
    document.filename = buffer
    period = f'{start:%d/%m/%Y} to {end:%d/%m/%Y}'
    document.build(story, onFirstPage=page_furniture(period), onLaterPages=page_furniture(period))
    return buffer.getvalue()
