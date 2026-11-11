"""What is due and what is already ticked on one day: the data for the daily screen."""

from django.utils import timezone

from . import rules
from .models import CleaningCheck, CleaningTask


def day_status(day):
    live = CleaningCheck.objects.filter(voided=False).select_related('recorded_by')
    done_today = {}
    for check in live.filter(date=day).order_by('number'):
        done_today.setdefault(check.task_id, []).append(check)

    tasks = []
    # Deactivated tasks only show if they were ticked that day.
    for task in CleaningTask.objects.all():
        if not task.active and task.pk not in done_today:
            continue
        last = live.filter(task=task, date__lte=day).order_by('-date').first()
        times = done_today.get(task.pk, [])
        tasks.append({
            'id': task.pk,
            'name': task.name,
            'frequency': task.frequency,
            'frequency_label': task.get_frequency_display(),
            'repeatable': task.repeatable,
            'due': rules.is_due(task.frequency, day, last.date if last else None),
            'done': bool(times),
            # Each time it was done that day (a repeatable task can have several).
            'times': [
                {
                    'number': check.number,
                    'done_by': check.recorded_by.name,
                    'at': timezone.localtime(check.recorded_at).strftime('%I:%M %p').lstrip('0').lower(),
                    'note': check.note,
                }
                for check in times
            ],
            'last_done': last.date if last else None,
        })
    return {'date': day, 'working_day': rules.is_working_day(day), 'tasks': tasks}
