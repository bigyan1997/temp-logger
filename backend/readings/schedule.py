"""When the storage readings are due (from paper Table 9).

Days are numbered like Python's weekday(): Monday is 0 and Sunday is 6.
Times are Sydney local time.
"""

from datetime import datetime, time, timedelta

from django.utils import timezone

from setup.closed_days import afternoon_instead_of_evening

STORAGE_SLOTS = {
    6: [time(21, 0)],                  # Sunday
    0: [time(9, 0), time(21, 0)],      # Monday
    1: [time(9, 0), time(21, 0)],      # Tuesday
    2: [time(9, 0), time(21, 0)],      # Wednesday
    3: [time(9, 0), time(21, 0)],      # Thursday
    4: [time(9, 0), time(15, 0)],      # Friday
}

EVENING = time(21, 0)
AFTERNOON = time(15, 0)  # replaces the evening reading on the day before a public holiday

# A reading counts as missed once this long has passed after its scheduled time.
GRACE_PERIOD = timedelta(hours=2)


def is_storage_slot(moment):
    """True if `moment` (a timezone-aware datetime) is exactly a storage reading time: the usual ones, or the
    3 pm reading taken the day before a public holiday."""
    local = timezone.localtime(moment)
    if local.second or local.microsecond:
        return False
    if local.time() in STORAGE_SLOTS.get(local.weekday(), []):
        return True
    return local.time() == AFTERNOON and afternoon_instead_of_evening(local.date())  # the only time that needs a look-up


def slots_on(day):
    """The storage readings that are due on a date, as timezone-aware datetimes.

    The day before a public holiday (Monday to Thursday) has 3 pm instead of 9 pm, because nobody is in at night."""
    times = STORAGE_SLOTS.get(day.weekday(), [])
    if afternoon_instead_of_evening(day):
        times = [AFTERNOON if t == EVENING else t for t in times]
    return [timezone.make_aware(datetime.combine(day, t)) for t in times]
