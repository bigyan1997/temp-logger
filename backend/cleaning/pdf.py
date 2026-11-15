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
HEAD_LEFT = ParagraphStyle('HeadLeft', parent=HEAD, alignment=0)
NOTE = ParagraphStyle('Note', parent=STYLES['Normal'], fontSize=8, leading=10, spaceAfter=2)
NOTE_TITLE = ParagraphStyle('NoteTitle', parent=NOTE, spaceAfter=3, keepWithNext=1)  # the title never sits alone at a page end
GREY = colors.HexColor('#e6e6e6')
TICK = '<font name="ZapfDingbats">4</font>'  # a check mark, which the normal fonts do not have


def lines(text):
    """Safe to put in a Paragraph, keeping the line breaks of a note."""
    return escape(text).replace('\r', '').replace('\n', '<br/>')


def detail_table(title, text_heading, checks, text_of, width):
    """A tidy table under the schedule: Date, Task, the note (or void reason) and who did it.
    A note with several lines stays together in its own cell, so it is clear where each one starts and ends."""
    date_width, task_width, by_width = 20 * mm, 55 * mm, 28 * mm
    rows = [[Paragraph(heading, HEAD_LEFT) for heading in ('Date', 'Task', text_heading, 'Done by')]]
    for check in checks:
        rows.append([
            Paragraph(f'{check.date:%d/%m/%y}', CELL),
            Paragraph(escape(check.task.name), CELL),
            Paragraph(lines(text_of(check)), CELL),
            Paragraph(escape(check.recorded_by.name), CELL),
        ])
    table = Table(rows, colWidths=[date_width, task_width, width - date_width - task_width - by_width, by_width], repeatRows=1)
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), GREY),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    return [Paragraph(f'<b>{title}</b>', NOTE_TITLE), table, Spacer(1, 4 * mm)]


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
    notes = sorted((check for check in live if check.note), key=lambda check: (check.date, check.pk))
    if notes:
        story += detail_table('Notes', 'Note', notes, lambda check: check.note, width)
    if voided:
        story += detail_table('Voided entries (not counted above)', 'Reason', voided, lambda check: check.void_reason, width)

    buffer = BytesIO()
    document.filename = buffer
    furniture = page_furniture(f'{start:%d/%m/%Y} to {end:%d/%m/%Y}')
    document.build(story, onFirstPage=furniture, onLaterPages=furniture)
    return buffer.getvalue()
