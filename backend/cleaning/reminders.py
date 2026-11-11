"""Monthly and quarterly tasks that are due (forklift recharge, pest spray, bait change): for the notices in the
app and the reminder emails (alerts/cleaning_check.py).

The rules for when a task is due are in rules.py. A due task stays due until it is ticked, and is called overdue
after OVERDUE_AFTER_DAYS. A due date that falls on a weekend or a public holiday in Settings moves to the next
working day."""

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
    """The tasks (with notices switched on) that are due now, oldest first."""
    found = []
    tasks = CleaningTask.objects.filter(active=True, notify=True).exclude(frequency=Frequency.DAILY)
    for task in tasks:
        last = CleaningCheck.objects.filter(task=task, voided=False, date__lte=today).order_by('-date').first()
        last_done = last.date if last else None
        if rules.is_done(task.frequency, last_done, today):
            continue
        due_date = first_working_day(rules.due_date(task.frequency, last_done, today))
        if today < due_date:
            continue
        days_late = (today - due_date).days
        found.append({
            'task': task,
            'due_date': due_date,
            'days_late': days_late,
            'state': 'overdue' if days_late >= OVERDUE_AFTER_DAYS else 'due',
            'last_done': last_done,
        })
    return sorted(found, key=lambda item: item['due_date'])
