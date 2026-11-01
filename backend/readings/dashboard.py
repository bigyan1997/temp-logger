"""The numbers and lists behind the admin dashboard."""

from datetime import timedelta

from django.utils import timezone

from setup.models import Supplier, Unit

from .choices import Status
from .models import CorrectiveAction, DispatchReading, ReceivingCheck, StorageReading
from .schedule import GRACE_PERIOD, slots_on

MISSED_LOOKBACK_DAYS = 2    # today and yesterday
OUT_OF_LIMIT_LOOKBACK = timedelta(days=7)


def missed_storage_slots(now):
    """Scheduled storage readings whose grace period has passed with nothing logged.

    Returns [{'unit': Unit, 'slot': datetime}], oldest first. A slot only counts
    once `GRACE_PERIOD` has passed, so a reading that is merely due is not "missed".
    """
    today = timezone.localtime(now).date()
    first_day = today - timedelta(days=MISSED_LOOKBACK_DAYS - 1)

    slots = []
    for offset in range(MISSED_LOOKBACK_DAYS):
        day = first_day + timedelta(days=offset)
        slots += [slot for slot in slots_on(day) if now >= slot + GRACE_PERIOD]

    logged = set(
        StorageReading.objects.filter(slot__in=slots, voided=False).values_list('unit_id', 'slot')
    )
    return [
        {'unit': unit, 'slot': slot}
        for slot in slots
        for unit in Unit.objects.filter(active=True)
        if (unit.pk, slot) not in logged
    ]


def out_of_limit_readings(now):
    """Out-of-limit readings from the last week, newest first, as simple dicts."""
    since = now - OUT_OF_LIMIT_LOOKBACK
    found = []
    for model, kind in [(StorageReading, 'storage'), (ReceivingCheck, 'receiving'), (DispatchReading, 'dispatch')]:
        readings = model.objects.filter(
            status=Status.OUT_OF_LIMIT, voided=False, recorded_at__gte=since
        ).select_related('recorded_by', 'corrective_action')
        for reading in readings:
            found.append({
                'kind': kind,
                'summary': str(reading),
                'recorded_at': reading.recorded_at,
                'recorded_by': reading.recorded_by.name,
                'action': reading.corrective_action.get_action_display(),
                'signed_off': reading.corrective_action.signed_off_at is not None,
            })
    return sorted(found, key=lambda r: r['recorded_at'], reverse=True)


def logged_today(now):
    """How many readings of all kinds were saved today."""
    today = timezone.localtime(now).date()
    return sum(
        model.objects.filter(recorded_at__date=today, voided=False).count()
        for model in (StorageReading, ReceivingCheck, DispatchReading)
    )


def progress_today(today):
    """How much of today's logging is done: storage slots, suppliers checked, runs sent out."""
    slots = slots_on(today)
    units = Unit.objects.filter(active=True).count()
    return {
        'storage': {
            'done': StorageReading.objects.filter(slot__in=slots, voided=False).count(),
            'total': len(slots) * units,
        },
        'receiving': {
            'done': ReceivingCheck.objects.filter(date=today, voided=False).count(),
            'total': Supplier.objects.filter(active=True).count(),
        },
        'dispatch': {'done': DispatchReading.objects.filter(date=today, voided=False).count()},
    }


def build_dashboard(now=None):
    now = now or timezone.now()
    today = timezone.localtime(now).date()
    missed = missed_storage_slots(now)
    out_of_limit = out_of_limit_readings(now)
    awaiting = CorrectiveAction.objects.live().filter(signed_off_at__isnull=True).count()

    return {
        'tiles': {
            'missed': len(missed),
            'out_of_limit': len(out_of_limit),
            'awaiting_signoff': awaiting,
            'logged_today': logged_today(now),
        },
        'today': progress_today(today),
        'missed': [{'unit': m['unit'].name, 'slot': m['slot']} for m in missed],
        'out_of_limit': out_of_limit,
    }
