"""The calibration rules from the HACCP plan (Table 14, and Table 15's 6-monthly schedule)."""

import calendar
from datetime import date
from decimal import Decimal

TOLERANCE = Decimal('1.0')   # thermometers must be accurate to +/-1 °C
ICE_POINT = Decimal('0')     # iced water reads 0 °C
EVERY_MONTHS = 6
NOTICE_DAYS = 15             # the "due soon" notice starts this many days before the due date


def probe_difference(reading):
    return reading - ICE_POINT


def within_margin(difference):
    return abs(difference) <= TOLERANCE


def add_months(day, months):
    """The same day number some months later, or the month's last day when it is shorter (31 Aug + 6 -> 28 Feb)."""
    index = day.month - 1 + months
    year, month = day.year + index // 12, index % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def due_state(last_pass, today):
    """Where the 6-monthly calibration stands. last_pass is the date of the latest passed, unvoided one.

    Returns {'state': never | ok | due_soon | overdue, 'due': date or None, 'days_left': int or None}.
    A calibration that failed does not count: it still needs a pass."""
    if last_pass is None:
        return {'state': 'never', 'due': None, 'days_left': None}
    due = add_months(last_pass, EVERY_MONTHS)
    days_left = (due - today).days
    state = 'overdue' if days_left < 0 else 'due_soon' if days_left <= NOTICE_DAYS else 'ok'
    return {'state': state, 'due': due, 'days_left': days_left}
