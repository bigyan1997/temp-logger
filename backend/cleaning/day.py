"""What is due and what is already ticked on one day: the data for the daily screen."""

from . import rules
from .models import CleaningCheck, CleaningTask


def day_status(day):
    live = CleaningCheck.objects.filter(voided=False).select_related('recorded_by')
    done_today = {check.task_id: check for check in live.filter(date=day)}

    tasks = []
    # Deactivated tasks only show if they were ticked that day.
    for task in CleaningTask.objects.all():
        if not task.active and task.pk not in done_today:
            continue
        period = rules.period_start(task.frequency, day)
        last = live.filter(task=task, date__gte=period, date__lte=day).order_by('-date').first()
        check = done_today.get(task.pk)
        tasks.append({
            'id': task.pk,
            'name': task.name,
            'frequency': task.frequency,
            'frequency_label': task.get_frequency_display(),
            'due': rules.is_due(task.frequency, day, last is not None),
            'done': check is not None,
            'done_by': check.recorded_by.name if check else '',
            'note': check.note if check else '',
            'last_done': last.date if last else None,
        })
    return {'date': day, 'working_day': rules.is_working_day(day), 'tasks': tasks}
