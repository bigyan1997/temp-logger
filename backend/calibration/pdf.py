"""Draws one calibration as a PDF that follows the paper Table 14 (HACCP Plan 1.6)."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from reports.pdf import COMPANY, HEADING, page_furniture

from . import rules

STYLES = getSampleStyleSheet()
BODY = ParagraphStyle('Body', parent=STYLES['Normal'], fontSize=9, leading=12, spaceAfter=3)
STEP = ParagraphStyle('Step', parent=BODY, leftIndent=14, spaceAfter=1)
GREY = colors.HexColor('#e6e6e6')

STEPS = [
    'Fill a cup with crushed ice or small ice cubes and add a little water (no more than 1/3 of the ice quantity) to make ice slurry',
    'Place thermometer probe in the centre of the cup so it touches the ice and water, but does not touch the base of the cup',
    'Leave for 5-10 minutes, then stir',
    'Take the reading. If the thermometer is accurate it should read 0°C',
]


def signed(value):
    return f'{value:+.1f} °C' if value else '0.0 °C'


def box(rows, width, spans=()):
    """A small grid like the paper's, with a grey heading row. Three equal-ish columns."""
    table = Table(rows, colWidths=[width * 0.34, width * 0.33, width * 0.33])
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), GREY),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        *[('SPAN', start, end) for start, end in spans],
    ]))
    return table


def probe_section(calibration, width):
    rows = [
        ['Probe thermometer calibration', '(0°C)', '(Comments)'],
        ['Date', f'{calibration.date:%d/%m/%Y}', ''],
        ['Temperature', f'{calibration.probe_reading} °C', Paragraph(escape(calibration.probe_comment), BODY)],
        ['Temperature difference', signed(rules.probe_difference(calibration.probe_reading)), ''],
        ['Signature', calibration.recorded_by.name, ''],
    ]
    story = [box(rows, width, spans=[((1, 4), (2, 4))]), Spacer(1, 3 * mm)]
    if calibration.passed:
        story.append(Paragraph(
            f'Result: within the margin of error (±{rules.TOLERANCE} °C). Allow for the difference when reading temperatures.', BODY))
    else:
        story.append(Paragraph(
            f'<font color="#8c1020"><b>Result: OUTSIDE the margin of error (±{rules.TOLERANCE} °C).</b></font> '
            f'Action: {escape(calibration.get_action_display())}. {escape(calibration.action_notes)}', BODY))
    return story


def gauge_section(calibration, width):
    gauges = list(calibration.gauges.select_related('unit'))
    if not gauges:
        return [Paragraph('No coolroom or freezer gauges were checked on this date.', BODY)]
    story = []
    for gauge in gauges:
        name = gauge.unit.name
        rows = [
            [f'{name} thermometer calibration', f'{name} temperature', 'Thermometer'],
            ['Date', f'{calibration.date:%d/%m/%Y}', ''],
            ['Temperature', f'{gauge.gauge_reading} °C', f'{gauge.probe_reading} °C'],
            ['Temperature difference', signed(gauge.difference), ''],
            ['Signature', calibration.recorded_by.name, ''],
        ]
        story.append(box(rows, width, spans=[((1, 1), (2, 1)), ((1, 3), (2, 3)), ((1, 4), (2, 4))]))
        if gauge.comment:
            story.append(Paragraph(f'<i>Comment:</i> {escape(gauge.comment)}', BODY))
        story.append(Spacer(1, 4 * mm))
    return story


def render_calibration(calibration):
    """The finished PDF as bytes."""
    document = SimpleDocTemplate(
        BytesIO(), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=16 * mm,
        title=f'{COMPANY} - Table 14 Thermometer calibration',
    )
    width = A4[0] - document.leftMargin - document.rightMargin

    story = [Paragraph('14. Table 14: Thermometer calibration', HEADING)]
    if calibration.voided:
        story.append(Paragraph(f'<font color="#8c1020"><b>VOIDED: {escape(calibration.void_reason)}</b></font>', BODY))
    story += [
        Paragraph(
            'Thermometers must be accurate to +/-1°C. Temperature measuring devices should be calibrated every six months '
            'by a nominated person and results recorded.', BODY),
        Paragraph('<b>Calibrating a handheld probe thermometer</b>', BODY),
        Paragraph('Handheld thermometers can be calibrated using the ice point check.', BODY),
        *[Paragraph(f'{number}. {text}', STEP) for number, text in enumerate(STEPS, start=1)],
        Spacer(1, 3 * mm),
        *probe_section(calibration, width),
        Paragraph(
            '<b>Acceptable margin of error (tolerance):</b> if thermometers are less than 1°C over or under the correct '
            'reading (eg +/-0.5°C, +/-1°C), the temperature difference should be noted and allowed for when reading the '
            'temperature for monitoring purposes.', BODY),
        Paragraph(
            '<b>Corrective action for being outside margin of error:</b> if thermometers are more than 1°C over or under '
            'the correct reading (eg +/-2°C), they should be replaced or repaired.', BODY),
        Spacer(1, 3 * mm),
        Paragraph('<b>Other thermometers and gauges</b>', BODY),
        Paragraph(
            'The calibrated handheld thermometer is used to check the accuracy of the fridge, freezer and coolroom gauges. '
            "It is left switched on inside the unit and its reading compared with the unit's own gauge. "
            'Any differences in readings are noted.', BODY),
        *gauge_section(calibration, width),
    ]

    buffer = BytesIO()
    document.filename = buffer
    furniture = page_furniture(f'{calibration.date:%d/%m/%Y}')
    document.build(story, onFirstPage=furniture, onLaterPages=furniture)
    return buffer.getvalue()
