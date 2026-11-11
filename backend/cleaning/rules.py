"""When a cleaning task is due. Plain functions with no database, so they are easy to test.

- Every working day: due Monday to Friday.
- Monthly (forklift recharge, 1st of the month): due from the 1st of each calendar month until it is ticked that month.
- Quarterly (pest spray, bait change): due three months after it was last done, so done on 10 September means due
  on 10 December. A quarterly task that has never been done is due now."""

from calibration.rules import add_months

from .models import Frequency

QUARTER_MONTHS = 3


def period_start(frequency, day):
    """The day a monthly task's month began (for the others, the day itself)."""
    if frequency == Frequency.MONTHLY:
        return day.replace(day=1)
    return day


def is_working_day(day):
    return day.weekday() < 5  # Monday to Friday, like the paper table


def is_done(frequency, last_done, today):
    """Monthly or quarterly: has it been done recently enough that it is not due yet? `last_done` is the latest tick."""
    if last_done is None:
        return False
    if frequency == Frequency.MONTHLY:
        return last_done >= period_start(frequency, today)
    return today < add_months(last_done, QUARTER_MONTHS)


def due_date(frequency, last_done, today):
    """The day a monthly or quarterly task fell due (not yet moved off a weekend or holiday)."""
    if frequency == Frequency.QUARTERLY and last_done is not None:
        return add_months(last_done, QUARTER_MONTHS)
    if frequency == Frequency.QUARTERLY:
        return today.replace(month=3 * ((today.month - 1) // 3) + 1, day=1)  # never done: since this quarter began
    return period_start(frequency, today)


def is_due(frequency, day, last_done):
    if frequency == Frequency.DAILY:
        return is_working_day(day)
    return not is_done(frequency, last_done, day)
