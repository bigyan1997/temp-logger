"""Monthly and quarterly tasks that are due (forklift recharge, pest spray, bait change): for the notices in the
app and the reminder emails (alerts/cleaning_check.py).

A task is due from the first working day of its month or quarter, and stays due until it is ticked. After
OVERDUE_AFTER_DAYS it is called overdue. Weekends and the public holidays in Settings are not working days."""

from datetime import timedelta

from setup.models import ClosedDay

from . import rules
from .models import CleaningCheck, CleaningTask, Frequency

OVERDUE_AFTER_DAYS = 7  # the email reminder repeats every this many days too


def first_working_day(day):
    closed = set(ClosedDay.objects.filter(active=True, date__gte=day, date__lte=day + timedelta(days=14)).values_list('date', flat=True))
    while not rules.is_working_day(day) or day in closed:
        day += timedelta(days=1)
    return day


def due_tasks(today):
    """The tasks (with notices switched on) that are due and not yet done this month or quarter, oldest first."""
    found = []
    tasks = CleaningTask.objects.filter(active=True, notify=True).exclude(frequency=Frequency.DAILY)
    for task in tasks:
        period = rules.period_start(task.frequency, today)
        due_date = first_working_day(period)
        if today < due_date:
            continue
        checks = CleaningCheck.objects.filter(task=task, voided=False, date__gte=period)
        if checks.exists():
            continue
        last = CleaningCheck.objects.filter(task=task, voided=False).order_by('-date').first()
        days_late = (today - due_date).days
        found.append({
            'task': task,
            'period': period,
            'due_date': due_date,
            'days_late': days_late,
            'state': 'overdue' if days_late >= OVERDUE_AFTER_DAYS else 'due',
            'last_done': last.date if last else None,
        })
    return sorted(found, key=lambda item: item['due_date'])
