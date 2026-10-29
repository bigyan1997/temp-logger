"""When the storage readings are due (from paper Table 9).

Days are numbered like Python's weekday(): Monday is 0 and Sunday is 6.
Times are Sydney local time.
"""

from datetime import datetime, time, timedelta

from django.utils import timezone

STORAGE_SLOTS = {
    6: [time(21, 0)],                  # Sunday
    0: [time(9, 0), time(21, 0)],      # Monday
    1: [time(9, 0), time(21, 0)],      # Tuesday
    2: [time(9, 0), time(21, 0)],      # Wednesday
    3: [time(9, 0), time(21, 0)],      # Thursday
    4: [time(9, 0), time(15, 0)],      # Friday
}

# A reading counts as missed once this long has passed after its scheduled time.
GRACE_PERIOD = timedelta(hours=2)


def is_storage_slot(moment):
    """True if `moment` (a timezone-aware datetime) is exactly a scheduled storage reading time."""
    local = timezone.localtime(moment)
    if local.second or local.microsecond:
        return False
    return local.time() in STORAGE_SLOTS.get(local.weekday(), [])


def slots_on(day):
    """The scheduled storage reading times on a date, as timezone-aware datetimes."""
    return [timezone.make_aware(datetime.combine(day, t)) for t in STORAGE_SLOTS.get(day.weekday(), [])]
