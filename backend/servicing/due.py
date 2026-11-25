"""When each piece of equipment is next due for service: 6 months after its latest service record.

Only routine services count: a repair does not move the due date.

Equipment is typed as free text, so "Coolroom" and "coolroom " count as the same piece. One record can cover several
pieces separated by commas ("Coolroom, Freezer"): each of them is serviced by that visit and gets its own due date."""

from calibration.rules import add_months

from .models import ServiceKind, ServiceRecord

EVERY_MONTHS = 6
NOTICE_DAYS = 15  # the "due soon" notice starts this many days before the due date (same as calibration)


def equipment_due(today):
    """One entry per piece of equipment, soonest due first: its name, last service, due date and state."""
    latest = {}  # equipment key -> (name as typed, record)
    for record in ServiceRecord.objects.filter(kind=ServiceKind.SERVICE).order_by('service_date', 'id'):
        for name in record.equipment.split(','):
            if name.strip():
                latest[name.strip().lower()] = (name.strip(), record)  # later records replace earlier ones
    found = []
    for name, record in latest.values():
        due = add_months(record.service_date, EVERY_MONTHS)
        days_left = (due - today).days
        state = 'overdue' if days_left < 0 else 'due_soon' if days_left <= NOTICE_DAYS else 'ok'
        found.append({
            'equipment': name, 'last_service': record.service_date, 'due': due,
            'days_left': days_left, 'state': state, 'record': record.number,
        })
    return sorted(found, key=lambda item: item['due'])
