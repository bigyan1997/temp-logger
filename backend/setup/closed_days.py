"""Which days and storage readings are closed (public holidays). The one place that knows the rule.

For a closed day:
  - its daytime storage readings are not due, and neither is the evening reading the night before;
  - its own evening reading IS still due, because deliveries go out the next morning;
  - Receiving and Dispatch are skipped for the whole date;
  - on the day before (Monday to Thursday) nobody is in at 9 pm, so a 3 pm reading is taken instead.
    Sunday has no 3 pm reading: its 9 pm reading is simply skipped.

Each function returns the label to show ("Public holiday"), or None when it is open as normal."""

from datetime import time, timedelta

from django.utils import timezone

from .models import ClosedDay

EVENING_FROM = time(18, 0)  # the 9 pm readings; the 9 am and Friday 3 pm ones are daytime
BEFORE_A_HOLIDAY_WEEKDAYS = (0, 1, 2, 3)  # Monday to Thursday; Friday already has a 3 pm reading


def closed_labels():
    """{date: label} for every active closed day. A short list, so it is read whole."""
    return dict(ClosedDay.objects.filter(active=True).values_list('date', 'label'))


def afternoon_instead_of_evening(day, closed=None):
    """True if this date (Monday to Thursday) has its 9 pm reading moved to 3 pm because the next day is closed."""
    if day.weekday() not in BEFORE_A_HOLIDAY_WEEKDAYS:
        return False
    closed = closed_labels() if closed is None else closed
    return (day + timedelta(days=1)) in closed


def storage_closure(slot, closed=None):
    """The label if this storage reading time is closed. Pass `closed` (from closed_labels) when checking many."""
    closed = closed_labels() if closed is None else closed
    local = timezone.localtime(slot)
    if local.time() >= EVENING_FROM:
        return closed.get(local.date() + timedelta(days=1))  # closed because the next day is
    return closed.get(local.date())


def day_closure(day, closed=None):
    """The label if Receiving and Dispatch are skipped on this date."""
    closed = closed_labels() if closed is None else closed
    return closed.get(day)
