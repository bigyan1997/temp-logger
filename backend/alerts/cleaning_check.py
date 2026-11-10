"""Emails about monthly and quarterly cleaning tasks: once when one becomes due, then again every 7 days while
it is still not done. Each is sent once (the key says which task, which period and which reminder)."""

from django.utils import timezone

from cleaning.reminders import OVERDUE_AFTER_DAYS, due_tasks

from .checks import Alert


def cleaning_alerts(now):
    found = []
    for item in due_tasks(timezone.localdate(now)):
        task, period, due_date = item['task'], item['period'], item['due_date']
        reminder = item['days_late'] // OVERDUE_AFTER_DAYS  # 0 on the first day, 1 a week later, and so on
        key = f'{task.pk}:{period.isoformat()}:{reminder}'
        if reminder == 0:
            lead = f'{task.name} (Table 8) is due. It is {task.get_frequency_display().lower()}.'
            found.append(Alert('cleaning_due', key, f'Due: {task.name}', lead, lead=lead, tone='reminder'))
        else:
            lead = f'{task.name} (Table 8) was due on {due_date:%A %d %B %Y} and has not been ticked off.'
            found.append(Alert('cleaning_late', key, f'OVERDUE: {task.name}', lead, lead=lead, tone='failed'))
    return found
