"""Works out which alerts are due right now. Each one is (kind, key, subject, body); the key is what
makes it unique, so it is only ever emailed once (see sender.py)."""

from collections import namedtuple
from datetime import timedelta

from django.utils import timezone

from readings.choices import Status
from readings.dashboard import missed_storage_slots
from readings.models import CorrectiveAction, DispatchReading, ReceivingCheck, StorageReading
from readings.schedule import GRACE_PERIOD, slots_on
from setup.models import Unit

REMIND_BEFORE = timedelta(minutes=15)   # "almost time to log"
SIGN_OFF_AFTER = timedelta(hours=2)      # a corrective action nobody has approved yet
LOOK_BACK = timedelta(hours=6)           # never email about things older than this (e.g. after the PC was off)

Alert = namedtuple('Alert', 'kind key subject body')


def clock(moment):
    return f'{timezone.localtime(moment):%I:%M %p}'.lstrip('0')


def unlogged_units(slot):
    logged = StorageReading.objects.filter(slot=slot, voided=False).values_list('unit_id', flat=True)
    return list(Unit.objects.filter(active=True).exclude(pk__in=logged))


def reminders(now):
    """A storage reading is due within 15 minutes and some units are not logged yet."""
    found = []
    for slot in slots_on(timezone.localtime(now).date()):
        if slot - REMIND_BEFORE <= now < slot:
            units = unlogged_units(slot)
            if units:
                names = ', '.join(unit.name for unit in units)
                found.append(Alert(
                    'reminder', slot.isoformat(), f'Storage temperatures due at {clock(slot)}',
                    f'Storage temperatures are due at {clock(slot)} ({timezone.localtime(slot):%A}).\n'
                    f'Still to log: {names}.',
                ))
    return found


def missed(now):
    """A storage reading was not logged within the 2-hour grace period."""
    by_slot = {}
    for item in missed_storage_slots(now):
        if now - item['slot'] <= GRACE_PERIOD + LOOK_BACK:
            by_slot.setdefault(item['slot'], []).append(item['unit'].name)
    return [
        Alert(
            'missed', slot.isoformat(), f'MISSED: storage temperatures due {clock(slot)}',
            f'The {clock(slot)} storage temperatures ({timezone.localtime(slot):%A %d/%m}) were not logged.\n'
            f'Missing: {", ".join(names)}.',
        )
        for slot, names in by_slot.items()
    ]


def out_of_limit(now):
    """A reading was saved out of limit (it always comes with a corrective action)."""
    found = []
    models = [(StorageReading, 'storage'), (ReceivingCheck, 'receiving'), (DispatchReading, 'dispatch')]
    for model, kind in models:
        readings = model.objects.filter(
            status=Status.OUT_OF_LIMIT, voided=False, recorded_at__gte=now - LOOK_BACK
        ).select_related('recorded_by', 'corrective_action')
        for reading in readings:
            action = reading.corrective_action
            notes = f'\nNotes: {action.notes}' if action.notes else ''
            found.append(Alert(
                'out_of_limit', f'{kind}-{reading.pk}', f'OUT OF LIMIT: {reading}',
                f'{reading}\nLogged by {reading.recorded_by.name} at {clock(reading.recorded_at)}.\n'
                f'Action taken: {action.get_action_display()}.{notes}',
            ))
    return found


def waiting_for_sign_off(now):
    """A corrective action has had no manager sign-off for 2 hours."""
    actions = CorrectiveAction.objects.live().filter(
        signed_off_at__isnull=True, created_at__lte=now - SIGN_OFF_AFTER, created_at__gte=now - LOOK_BACK
    )
    return [
        Alert(
            'sign_off', str(action.pk), f'Waiting for sign-off: {action.reading}',
            f'{action.reading} has been waiting for a manager to sign it off since {clock(action.created_at)}.',
        )
        for action in actions
    ]


def due_alerts(now):
    return reminders(now) + missed(now) + out_of_limit(now) + waiting_for_sign_off(now)
