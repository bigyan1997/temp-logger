"""Works out which alerts are due right now. Each one is (kind, key, subject, body); the key is what
makes it unique, so it is only ever emailed once (see sender.py)."""

from collections import namedtuple
from datetime import timedelta

from django.utils import timezone

from readings.models import StorageReading
from readings.schedule import slots_on
from setup.models import Unit

# For each scheduled storage reading: a first reminder just before it, and a second one if it is still not logged.
# 9 am: 8:30 am and 12 pm. 9 pm: 8:30 pm and 12 am. Friday 3 pm: 2:30 pm and 6 pm.
FIRST_REMINDER_BEFORE = timedelta(minutes=30)
SECOND_REMINDER_AFTER = timedelta(hours=3)
SECOND_REMINDER_WINDOW = timedelta(hours=1)  # still sent if the 5-minute task was delayed, but not hours later


# lead: the sentence under the heading. items: units still to log. tone: reminder, reminder2 or ok (the email's colours).
Alert = namedtuple('Alert', 'kind key subject body lead items tone', defaults=('', (), 'reminder'))


def clock(moment):
    return f'{timezone.localtime(moment):%I:%M %p}'.lstrip('0')


def unlogged_units(slot):
    logged = StorageReading.objects.filter(slot=slot, voided=False).values_list('unit_id', flat=True)
    return list(Unit.objects.filter(active=True).exclude(pk__in=logged))


def recent_slots(now):
    """Scheduled reading times from yesterday and today (the midnight reminder is about last night's reading)."""
    today = timezone.localtime(now).date()
    return slots_on(today - timedelta(days=1)) + slots_on(today)


def reminders(now):
    """A first reminder 30 minutes before a reading and a second 3 hours after it, while units are not logged."""
    found = []
    for slot in recent_slots(now):
        first_due = slot - FIRST_REMINDER_BEFORE <= now < slot
        second_due = slot + SECOND_REMINDER_AFTER <= now < slot + SECOND_REMINDER_AFTER + SECOND_REMINDER_WINDOW
        if not (first_due or second_due):
            continue
        units = unlogged_units(slot)
        if not units:
            continue

        names = ', '.join(unit.name for unit in units)
        when = f'{clock(slot)} ({timezone.localtime(slot):%A})'
        if first_due:
            found.append(Alert(
                'reminder', slot.isoformat(), f'Storage temperatures due at {clock(slot)}',
                f'Storage temperatures are due at {when}.\nStill to log: {names}.',
                lead=f'Storage temperatures are due at {when}.', items=tuple(unit.name for unit in units), tone='reminder',
            ))
        else:
            found.append(Alert(
                'reminder2', slot.isoformat(), f'STILL NOT LOGGED: storage temperatures due {clock(slot)}',
                f'The {when} storage temperatures have still not been logged.\nMissing: {names}.',
                lead=f'The {when} storage temperatures have still not been logged.',
                items=tuple(unit.name for unit in units), tone='reminder2',
            ))
    return found


def sample_alerts():
    """One example of every kind of alert, worded like the real ones, for checking that email works.

    Made up: nothing is read from or saved to the records.
    """
    return [
        Alert(
            'sample', 'reminder', 'TEST - Storage temperatures due at 9:00 PM',
            'Storage temperatures are due at 9:00 PM (Monday).\nStill to log: Coolroom, Freezer, Chest Freezer.',
            lead='Storage temperatures are due at 9:00 PM (Monday).', items=('Coolroom', 'Freezer', 'Chest Freezer'), tone='reminder',
        ),
        Alert(
            'sample', 'reminder2', 'TEST - STILL NOT LOGGED: storage temperatures due 9:00 PM',
            'The 9:00 PM (Monday) storage temperatures have still not been logged.\n'
            'Missing: Coolroom, Old Coolroom, Freezer, Chest Freezer.',
            lead='The 9:00 PM (Monday) storage temperatures have still not been logged.',
            items=('Coolroom', 'Old Coolroom', 'Freezer', 'Chest Freezer'), tone='reminder2',
        ),
    ]


def test_alert():
    """The message for `send_alerts --test`: proves email is set up, and shows how the emails look."""
    return Alert(
        'test', '', 'Test alert', 'Alert emails are working.',
        lead='Alert emails are working. Reminders for storage temperatures will arrive like this one.', tone='ok',
    )


def due_alerts(now):
    return reminders(now)
