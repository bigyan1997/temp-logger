"""When a cleaning task is due. Plain functions with no database, so they are easy to test."""

from .models import Frequency


def period_start(frequency, day):
    """The first day of the period `day` falls in: the day itself, its month, or its quarter."""
    if frequency == Frequency.MONTHLY:
        return day.replace(day=1)
    if frequency == Frequency.QUARTERLY:
        return day.replace(month=3 * ((day.month - 1) // 3) + 1, day=1)
    return day


def is_working_day(day):
    return day.weekday() < 5  # Monday to Friday, like the paper table


def is_due(frequency, day, done_in_period):
    """A daily task is due on working days. A monthly or quarterly one is due until it has been done in that period."""
    if frequency == Frequency.DAILY:
        return is_working_day(day)
    return not done_in_period
