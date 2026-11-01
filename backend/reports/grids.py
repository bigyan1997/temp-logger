"""The content of each report, laid out like the paper HACCP tables.

Everything here is plain data (no drawing), so it is easy to test; pdf.py draws it.

The paper sheets work in whole weeks that start on Sunday night:
  - Table 9 (storage):   4 weeks side by side on one page; each week has a column per unit.
  - Tables 10 and 11:    one row per day: a Sunday (night) row, then Monday to Friday.
So a report covers whole Sunday-to-Friday weeks that overlap the dates asked for.

A reading that was out of limit ends with "*".
"""

from datetime import datetime, timedelta

from django.utils import timezone

from readings.choices import Status
from readings.models import CorrectiveAction, DispatchReading, ReceivingCheck, StorageReading
from readings.schedule import STORAGE_SLOTS
from setup.models import Run, Supplier, Unit

MAX_DAYS = 186  # about 6 months
NO_DELIVERY = 'No delivery'
RUN_NOT_USED = 'Run not used'
WEEKS_PER_STORAGE_SHEET = 4
DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
STORAGE_DAY_ORDER = [6, 0, 1, 2, 3, 4]  # Sunday first, then Monday to Friday (Python weekday numbers)


def week_sundays(start, end):
    """The Sunday that starts each week overlapping start..end (weeks run Sunday to Friday)."""
    sunday = start - timedelta(days=(start.weekday() + 1) % 7)
    sundays = []
    while sunday <= end:
        if sunday + timedelta(days=5) >= start:  # skip a week that finished before the period began
            sundays.append(sunday)
        sunday += timedelta(days=7)
    return sundays


def clock_label(slot_time):
    """9.00 AM, 3.00 PM: the way the paper sheet writes times."""
    return f'{slot_time.hour % 12 or 12}.{slot_time.minute:02d} {"AM" if slot_time.hour < 12 else "PM"}'


def starred(reading, text):
    return f'{text}*' if reading.status == Status.OUT_OF_LIMIT else text


def columns(model, used_ids):
    """Active items, plus deactivated ones that still have readings in the period."""
    return [item for item in model.objects.all() if item.active or item.pk in used_ids]


# Table 9 -------------------------------------------------------------------

def storage_sheets(start, end):
    """A list of sheets, each holding up to four weeks. See the module note for the layout.

    sheet = {
        'units': [unit names],
        'weeks': [Sunday date or None] * 4,
        'rows':  [ {'kind': 'date', 'label': 'Monday / Date:', 'dates': [date or None] * 4},
                   {'kind': 'time', 'label': '9.00 AM', 'cells': [[one text per unit] per week]}, ... ],
    }
    """
    sundays = week_sundays(start, end)
    readings = StorageReading.objects.filter(
        slot__date__gte=sundays[0], slot__date__lte=sundays[-1] + timedelta(days=6), voided=False
    )
    by_slot = {(r.unit_id, r.slot): r for r in readings}
    units = columns(Unit, {r.unit_id for r in readings})

    sheets = []
    for first in range(0, len(sundays), WEEKS_PER_STORAGE_SHEET):
        group = sundays[first:first + WEEKS_PER_STORAGE_SHEET]
        weeks = group + [None] * (WEEKS_PER_STORAGE_SHEET - len(group))

        rows = []
        for weekday in STORAGE_DAY_ORDER:
            offset = (weekday + 1) % 7  # Sunday is 0 days after the week's Sunday, Friday is 5
            rows.append({
                'kind': 'date',
                'label': f'{DAY_NAMES[weekday]} / Date:',
                'dates': [week + timedelta(days=offset) if week else None for week in weeks],
            })
            for slot_time in STORAGE_SLOTS[weekday]:
                cells = []
                for week in weeks:
                    if week is None:
                        cells.append([''] * len(units))
                        continue
                    slot = timezone.make_aware(datetime.combine(week + timedelta(days=offset), slot_time))
                    cells.append([
                        starred(r, f'{r.value}') if (r := by_slot.get((unit.pk, slot))) else '' for unit in units
                    ])
                rows.append({'kind': 'time', 'label': clock_label(slot_time), 'cells': cells})

        sheets.append({'units': [unit.name for unit in units], 'weeks': weeks, 'rows': rows})
    return sheets


# Tables 10 and 11 ----------------------------------------------------------

def weekly_rows(sundays, entries, items, text_for, sunday_label):
    """A row for each day of each week: Sunday (night), then Monday to Friday.

    `entries` maps (item id, date) to a reading. `sunday_label` is what the Day column says on Sunday.
    """
    rows = []
    for sunday in sundays:
        for offset in range(0, 6):  # Sunday, then Monday to Friday
            day = sunday + timedelta(days=offset)
            rows.append({
                'day': sunday_label if offset == 0 else DAY_NAMES[day.weekday()],
                'date': day,
                'cells': [text_for(entries.get((item.pk, day))) for item in items],
                'new_week': offset == 0,
            })

        saturday = sunday + timedelta(days=6)
        cells = [text_for(entries.get((item.pk, saturday))) for item in items]
        if any(cells):  # there is no Saturday row on paper, so only add one if something was logged
            rows.append({'day': 'Saturday', 'date': saturday, 'cells': cells, 'new_week': False})
    return rows


def receiving_grid(start, end):
    """Table 10: a column per supplier, with a "Sunday night" row. "(pkg)" means packaging was not OK."""
    sundays = week_sundays(start, end)
    checks = ReceivingCheck.objects.filter(
        date__gte=sundays[0], date__lte=sundays[-1] + timedelta(days=6), voided=False
    )
    entries = {(c.supplier_id, c.date): c for c in checks}
    suppliers = columns(Supplier, {c.supplier_id for c in checks})

    def text_for(check):
        if check is None:
            return ''
        if check.no_delivery:
            return NO_DELIVERY
        text = f'{check.temp}'
        if not check.packaging_ok:
            text += ' (pkg)'
        return f'{text}*' if check.status == Status.OUT_OF_LIMIT or not check.packaging_ok else text

    return {'columns': [s.name for s in suppliers], 'rows': weekly_rows(sundays, entries, suppliers, text_for, 'Sunday night')}


def dispatch_grid(start, end, today=None):
    """Table 11: a column per run, with a "Sunday" row.

    A run with no reading on a day when other runs were logged was not used that day, and says so.
    A day with nothing logged at all is left blank (it may simply not have happened yet).
    """
    sundays = week_sundays(start, end)
    readings = DispatchReading.objects.filter(
        date__gte=sundays[0], date__lte=sundays[-1] + timedelta(days=6), voided=False
    )
    entries = {(r.run_id, r.date): r for r in readings}
    runs = columns(Run, {r.run_id for r in readings})

    def text_for(reading):
        return starred(reading, f'{reading.temp}') if reading else ''

    rows = weekly_rows(sundays, entries, runs, text_for, 'Sunday')
    for row in rows:
        if row['date'] < (today or timezone.localdate()) and any(row['cells']):
            row['cells'] = [cell or RUN_NOT_USED for cell in row['cells']]
    return {'columns': [f'Run {r.code}' for r in runs], 'rows': rows}


# Corrective actions listed under each report -------------------------------

def signed_off_text(action):
    """"Jessica, 30/10/2026", followed by her note when she signed off her own entry."""
    if not action.signed_off_at:
        return 'Not signed off'
    text = f'{action.signed_off_name}, {timezone.localtime(action.signed_off_at):%d/%m/%Y}'
    return f'{text} - {action.signed_off_note}' if action.signed_off_note else text


def logged_by(reading):
    """The person who took the reading and the login they used: "Sam (night)"."""
    shift = 'day' if reading.entered_by.role == 'admin' else 'night'
    return f'{reading.recorded_by.name} ({shift})'


def reading_date(reading):
    """The day a reading belongs to (a storage reading by its slot, in Sydney time)."""
    return timezone.localtime(reading.slot).date() if hasattr(reading, 'slot') else reading.date


def week_start(day):
    """The Sunday that starts the week containing `day` (weeks run Sunday to Saturday)."""
    return day - timedelta(days=(day.weekday() + 1) % 7)


def corrective_rows(start, end, kind):
    """Corrective actions in date order. `week_starts` has the Sunday of each row, so the PDF can group by week."""
    filters = {
        'storage': {'storage_reading__slot__date__range': (start, end), 'storage_reading__voided': False},
        'receiving': {'receiving_check__date__range': (start, end), 'receiving_check__voided': False},
        'dispatch': {'dispatch_reading__date__range': (start, end), 'dispatch_reading__voided': False},
    }[kind]
    actions = CorrectiveAction.objects.filter(**filters).select_related('signed_off_by', 'signed_off_person')
    for parent in ('storage_reading', 'receiving_check', 'dispatch_reading'):
        actions = actions.select_related(f'{parent}__recorded_by', f'{parent}__entered_by')

    ordered = sorted(actions, key=lambda action: (reading_date(action.reading), action.created_at))
    rows = [
        [str(a.reading), a.get_action_display(), a.notes, logged_by(a.reading), signed_off_text(a)] for a in ordered
    ]
    return {
        'headers': ['Reading', 'Action taken', 'Notes', 'Logged by', 'Signed off'],
        'rows': rows,
        'week_starts': [week_start(reading_date(a.reading)) for a in ordered],
    }


# kind -> (heading as on the paper sheet, function that builds the content)
REPORTS = {
    'storage': ('9.  Table 9 – Cold and Frozen Storage Recording', storage_sheets),
    'receiving': ('10.  Table 10 – Temperature & Packaging Integrity Check on Receiving Stock', receiving_grid),
    'dispatch': ('11.  Table 11 - Temperature Check on Dispatch', dispatch_grid),
}
