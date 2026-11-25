"""Emails about the 6-monthly equipment service: once when a service comes within 15 days, once if it goes overdue.

The key holds the due date, so after a new service is recorded (a new due date) the next round of emails starts again."""

from django.utils import timezone

from servicing.due import equipment_due

from .checks import Alert


def service_alerts(now):
    found = []
    for item in equipment_due(timezone.localdate(now)):
        name, due, days = item['equipment'], item['due'], item['days_left']
        key = f'{name.lower()[:50]}:{due.isoformat()}'
        if item['state'] == 'due_soon':
            when = 'today' if days == 0 else f'in {days} day' + ('' if days == 1 else 's')
            lead = f'{name} is due for its 6-monthly service on {due:%A %d %B %Y}, {when}.'
            found.append(Alert('service_due', key, f'Service due: {name} on {due:%d %B %Y}', lead, lead=lead, tone='reminder'))
        elif item['state'] == 'overdue':
            lead = f'{name} was due for its 6-monthly service on {due:%A %d %B %Y} and no new service has been recorded.'
            found.append(Alert('service_overdue', key, f'SERVICE OVERDUE: {name}', lead, lead=lead, tone='failed'))
    return found
