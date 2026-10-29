"""Everything the entry screens need to know about one day: what is due and what is already logged."""

from django.utils import timezone

from setup.models import Run, Supplier, Unit

from .models import DispatchReading, ReceivingCheck, StorageReading
from .schedule import GRACE_PERIOD, slots_on


def slot_state(slot, now, all_done):
    """done, upcoming (not due yet), due (inside the grace period) or missed."""
    if all_done:
        return 'done'
    if now < slot:
        return 'upcoming'
    return 'due' if now < slot + GRACE_PERIOD else 'missed'


def storage_for_day(day, now):
    slots = slots_on(day)
    units = list(Unit.objects.filter(active=True))
    logged = {
        (r.unit_id, r.slot): r
        for r in StorageReading.objects.filter(slot__in=slots, voided=False)
    }

    result = []
    for slot in slots:
        rows = []
        for unit in units:
            reading = logged.get((unit.pk, slot))
            rows.append({
                'unit_id': unit.pk,
                'name': unit.name,
                'kind': unit.kind,
                'limit': str(unit.max_temp),
                'reading': {'id': str(reading.pk), 'value': str(reading.value), 'status': reading.status}
                if reading else None,
            })
        all_done = all(row['reading'] for row in rows)
        result.append({'slot': slot, 'state': slot_state(slot, now, all_done), 'units': rows})
    return result


def receiving_for_day(day):
    checks = {c.supplier_id: c for c in ReceivingCheck.objects.filter(date=day, voided=False)}
    return [
        {
            'supplier_id': supplier.pk,
            'name': supplier.name,
            'entry': {
                'id': str(check.pk),
                'temp': str(check.temp) if check.temp is not None else None,
                'no_delivery': check.no_delivery,
                'status': check.status,
            } if (check := checks.get(supplier.pk)) else None,
        }
        for supplier in Supplier.objects.filter(active=True)
    ]


def dispatch_for_day(day):
    readings = {r.run_id: r for r in DispatchReading.objects.filter(date=day, voided=False)}
    return [
        {
            'run_id': run.pk,
            'code': run.code,
            'entry': {'id': str(reading.pk), 'temp': str(reading.temp), 'status': reading.status}
            if (reading := readings.get(run.pk)) else None,
        }
        for run in Run.objects.filter(active=True)
    ]


def build_day(day, now=None):
    now = now or timezone.now()
    return {
        'date': day,
        'storage': storage_for_day(day, now),
        'receiving': receiving_for_day(day),
        'dispatch': dispatch_for_day(day),
    }
