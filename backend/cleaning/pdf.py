"""Table 8 (Cleaning & Maintenance Schedule) as a PDF: a row for each working day, a column for each task."""

from datetime import timedelta
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from reports.pdf import COMPANY, HEADING, page_furniture

from .models import CleaningCheck, CleaningTask

STYLES = getSampleStyleSheet()
HEAD = ParagraphStyle('Head', parent=STYLES['Normal'], fontSize=6.5, leading=7.5, alignment=1)
CELL = ParagraphStyle('Cell', parent=STYLES['Normal'], fontSize=7, leading=8)
TICKED = ParagraphStyle('Ticked', parent=CELL, alignment=1)
NOTE = ParagraphStyle('Note', parent=STYLES['Normal'], fontSize=8, leading=10, spaceAfter=2)
GREY = colors.HexColor('#e6e6e6')
TICK = '<font name="ZapfDingbats">4</font>'  # a check mark, which the normal fonts do not have


def lines(text):
    """Safe to put in a Paragraph, keeping the line breaks of a note."""
    return escape(text).replace('\r', '').replace('\n', '<br/>')


def tick_text(times):
    """A tick, with x2, x3 when a task was done more than once that day."""
    if times == 0:
        return ''
    return TICK if times == 1 else f'{TICK} x{times}'


def days_shown(start, end, checked_days):
    """Every working day in the period, plus any weekend day that has something ticked."""
    days, day = [], start
    while day <= end:
        if day.weekday() < 5 or day in checked_days:
            days.append(day)
        day += timedelta(days=1)
    return days


def render_cleaning(start, end):
    """The finished PDF as bytes."""
    checks = list(CleaningCheck.objects.filter(date__gte=start, date__lte=end).select_related('task', 'recorded_by'))
    live = [check for check in checks if not check.voided]
    voided = [check for check in checks if check.voided]
    used = {check.task_id for check in live}
    tasks = [task for task in CleaningTask.objects.all() if task.active or task.pk in used]

    times_done = {}  # (task, day) -> how many times it was done
    for check in live:
        times_done[(check.task_id, check.date)] = times_done.get((check.task_id, check.date), 0) + 1
    names = {}
    for check in live:
        names.setdefault(check.date, set()).add(check.recorded_by.name)

    rows = [[Paragraph('Day / Date', HEAD)] + [Paragraph(escape(task.name), HEAD) for task in tasks] + [Paragraph('Done by', HEAD)]]
    for day in days_shown(start, end, {check.date for check in live}):
        row = [Paragraph(f'{day:%A} {day:%d/%m/%y}', CELL)]
        row += [Paragraph(tick_text(times_done.get((task.pk, day), 0)), TICKED) for task in tasks]
        row.append(Paragraph(escape(', '.join(sorted(names.get(day, [])))), CELL))
        rows.append(row)

    document = SimpleDocTemplate(
        BytesIO(), pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm, topMargin=16 * mm, bottomMargin=14 * mm,
        title=f'{COMPANY} - Table 8 Cleaning & Maintenance Schedule',
    )
    width = landscape(A4)[0] - document.leftMargin - document.rightMargin
    day_width, name_width = 30 * mm, 24 * mm
    task_width = (width - day_width - name_width) / max(len(tasks), 1)
    table = Table(rows, colWidths=[day_width] + [task_width] * len(tasks) + [name_width], repeatRows=1)
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), GREY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))

    story = [Paragraph('8. Table 8: Cleaning & Maintenance Schedule', HEADING), table, Spacer(1, 4 * mm)]
    notes = [check for check in live if check.note]
    if notes:
        story.append(Paragraph('<b>Notes</b>', NOTE))
        story += [Paragraph(f'{check.date:%d/%m/%y} {escape(check.task.name)}: {lines(check.note)}', NOTE) for check in notes]
    if voided:
        story.append(Paragraph('<b>Voided entries (not counted above)</b>', NOTE))
        story += [Paragraph(f'{check.date:%d/%m/%y} {escape(check.task.name)}: {lines(check.void_reason)}', NOTE) for check in voided]

    buffer = BytesIO()
    document.filename = buffer
    furniture = page_furniture(f'{start:%d/%m/%Y} to {end:%d/%m/%Y}')
    document.build(story, onFirstPage=furniture, onLaterPages=furniture)
    return buffer.getvalue()
