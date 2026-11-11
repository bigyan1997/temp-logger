"""Table 5 (Non-Conformance Report) as PDFs: one report laid out like the paper form, or a register of many."""

from io import BytesIO
from xml.sax.saxutils import escape

from PIL import Image as PilImage
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from reports.pdf import COMPANY, HEADING, page_furniture

from . import photos
from .models import NonConformance, Update

STYLES = getSampleStyleSheet()
BODY = ParagraphStyle('Body', parent=STYLES['Normal'], fontSize=9, leading=12, spaceAfter=3)
CELL = ParagraphStyle('Cell', parent=STYLES['Normal'], fontSize=8, leading=10)
HEAD = ParagraphStyle('Head', parent=CELL, fontName='Helvetica-Bold')
FORM_LABEL = ParagraphStyle('FormLabel', parent=CELL, fontSize=9.5, leading=12)
SMALL = ParagraphStyle('Small', parent=STYLES['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#555555'))
GREY = colors.HexColor('#e6e6e6')
RED = '#8c1020'
NO_ANSWER = '-'


def text(value):
    """Safe for a Paragraph, keeping line breaks."""
    return escape(value or '').replace('\r', '').replace('\n', '<br/>')


def when(moment):
    return f'{timezone.localtime(moment):%d/%m/%Y %I:%M %p}'.replace(' 0', ' ')


def live(report, kind):
    return [u for u in report.updates.all() if u.kind == kind and not u.voided]


def lines(updates, with_time=True):
    """One paragraph's worth of text for a group of follow-ups."""
    parts = []
    for update in updates:
        head = f'<b>{when(update.happened_at) if with_time else f"{timezone.localtime(update.happened_at):%d/%m/%Y}"}</b>'
        parts.append(head + (f'<br/>{text(update.text)}' if update.text else ''))  # the date on its own line, the note under it
    return '<br/><br/>'.join(parts) or NO_ANSWER


def signed_off(report):
    closed = live(report, Update.Kind.CLOSED)
    if not closed:
        return NO_ANSWER
    last = closed[-1]
    note = f'<br/>{text(last.text)}' if last.text else ''
    return f'{escape(last.recorded_by.name)}<br/>{timezone.localtime(last.happened_at):%d/%m/%Y}{note}'


def table_style(header=True):
    style = [
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]
    if header:
        style.append(('BACKGROUND', (0, 0), (-1, 0), GREY))
    return TableStyle(style)


def photo_flowables(photo_list, width):
    """The photos, two to a row, each with its file name. A file that cannot be drawn is just named."""
    pictures, problems = [], []
    for photo in photo_list:
        try:
            path = photos.full_path(photo.path)
            with PilImage.open(path) as opened:
                pixel_width, pixel_height = opened.size
            box_width, box_height = width / 2 - 8 * mm, 70 * mm
            scale = min(box_width / pixel_width, box_height / pixel_height)
            pictures.append([Image(str(path), pixel_width * scale, pixel_height * scale), Paragraph(escape(photo.original_name), SMALL)])
        except Exception:  # missing or unreadable file: say so instead of failing the whole PDF
            problems.append(photo.original_name)
    story = []
    for start in range(0, len(pictures), 2):
        row = pictures[start:start + 2]
        cells = [[item[0], item[1]] for item in row]
        table = Table([[Table([[cell[0]], [cell[1]]]) for cell in cells]], colWidths=[width / 2] * len(row))
        table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
        story += [table, Spacer(1, 3 * mm)]
    if problems:
        story.append(Paragraph('Photo file(s) could not be shown: ' + escape(', '.join(problems)), SMALL))
    return story


def render_report(report):
    """One report as a PDF: the rows of the paper table, with the photos inside them."""
    document = SimpleDocTemplate(
        BytesIO(), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=16 * mm,
        title=f'{COMPANY} - Table 5 Non-Conformance Report {report.number}',
    )
    width = A4[0] - document.leftMargin - document.rightMargin
    label_width = 52 * mm

    story = [Paragraph(f'5. Table 5 - Non-Conformance Report ({report.number})', HEADING)]
    if report.voided:
        story.append(Paragraph(f'<font color="{RED}"><b>VOIDED: {text(report.void_reason)}</b></font>', BODY))
    inner = width - label_width - 4 * mm
    live_photos = [p for p in report.photos.all() if not p.voided]
    description = [Paragraph(text(report.description), CELL)]
    own = [p for p in live_photos if p.update_id is None]
    if own:
        description += [Spacer(1, 3 * mm)] + photo_flowables(own, inner)  # photos sit in the description box, as on paper

    def with_photos(kind):
        """A follow-up row's text, then the photos that came with those follow-ups (e.g. the manufacturer's photo)."""
        ids = {u.pk for u in live(report, kind)}
        pictures = [p for p in live_photos if p.update_id in ids]
        return [Paragraph(lines(live(report, kind)), CELL)] + ([Spacer(1, 3 * mm)] + photo_flowables(pictures, inner) if pictures else [])
    # Same rows, in the same order and wording, as the paper form.
    rows = [
        ('Date', Paragraph(f'{report.date:%d/%m/%Y}', CELL)),
        ('Product Name / Code', Paragraph(text(report.product), CELL)),
        ('Customer', Paragraph(text(report.customer) or NO_ANSWER, CELL)),
        ('Manufacturer', Paragraph(text(report.manufacturer) or NO_ANSWER, CELL)),
        ('Description of Problem<br/>(attach photos if available)', description),
        ('Has manufacturer been notified.<br/>(specify date and time)', Paragraph(lines(live(report, Update.Kind.NOTIFIED)) if live(report, Update.Kind.NOTIFIED) else 'No', CELL)),  # a clear No, as the form asks yes or no
        ('Manufacturer Response', with_photos(Update.Kind.RESPONSE)),
        ('Specify further corrective action to be taken', with_photos(Update.Kind.ACTION)),
        ('Signed / Dated', Paragraph(signed_off(report), CELL)),
    ]
    table = Table([[Paragraph(label, FORM_LABEL), value] for label, value in rows], colWidths=[label_width, width - label_width])
    table.setStyle(table_style(header=False))
    story += [table, Spacer(1, 3 * mm),
              Paragraph(f'Reported by {escape(report.recorded_by.name)}, {when(report.recorded_at)}', SMALL), Spacer(1, 4 * mm)]

    buffer = BytesIO()
    document.filename = buffer
    furniture = page_furniture(f'{report.number} {report.date:%d/%m/%Y}')
    document.build(story, onFirstPage=furniture, onLaterPages=furniture)
    return buffer.getvalue()


def render_register(start, end):
    """Every report in the period as the paper Table 5: a row for each, a column for each of its questions."""
    reports = list(
        NonConformance.objects.filter(date__gte=start, date__lte=end, voided=False)
        .select_related('recorded_by').prefetch_related('updates__recorded_by', 'photos').order_by('date', 'id')
    )
    document = SimpleDocTemplate(
        BytesIO(), pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm, topMargin=16 * mm, bottomMargin=14 * mm,
        title=f'{COMPANY} - Table 5 Non-Conformance Report register',
    )
    width = landscape(A4)[0] - document.leftMargin - document.rightMargin
    names = ['No. / Date', 'Product name / code', 'Customer', 'Manufacturer', 'Description of problem',
             'Has manufacturer been notified (date and time)', 'Manufacturer response', 'Further corrective action', 'Signed / dated']
    shares = [0.08, 0.10, 0.08, 0.09, 0.19, 0.12, 0.13, 0.13, 0.08]
    rows = [[Paragraph(name, HEAD) for name in names]]
    for report in reports:
        photo_count = sum(1 for photo in report.photos.all() if not photo.voided)
        description = text(report.description) + (f'<br/><i>({photo_count} photo{"s" if photo_count != 1 else ""} attached)</i>' if photo_count else '')
        rows.append([
            Paragraph(f'<b>{report.number}</b><br/>{report.date:%d/%m/%Y}', CELL), Paragraph(text(report.product), CELL),
            Paragraph(text(report.customer) or NO_ANSWER, CELL), Paragraph(text(report.manufacturer) or NO_ANSWER, CELL),
            Paragraph(description, CELL), Paragraph(lines(live(report, Update.Kind.NOTIFIED)), CELL),
            Paragraph(lines(live(report, Update.Kind.RESPONSE)), CELL), Paragraph(lines(live(report, Update.Kind.ACTION)), CELL),
            Paragraph(signed_off(report), CELL),
        ])
    if not reports:
        rows.append([Paragraph('No non-conformance reports in this period.', CELL)] + [''] * (len(names) - 1))
    table = Table(rows, colWidths=[width * share for share in shares], repeatRows=1)
    table.setStyle(table_style())

    story = [Paragraph('5. Table 5: Non-Conformance Report', HEADING), table]
    buffer = BytesIO()
    document.filename = buffer
    furniture = page_furniture(f'{start:%d/%m/%Y} to {end:%d/%m/%Y}')
    document.build(story, onFirstPage=furniture, onLaterPages=furniture)
    return buffer.getvalue()
