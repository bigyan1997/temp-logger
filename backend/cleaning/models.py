from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from setup.models import Attributed


class Frequency(models.TextChoices):
    DAILY = 'daily', 'Every working day'
    MONTHLY = 'monthly', 'Once a month'
    QUARTERLY = 'quarterly', 'Once a quarter'


class CleaningTask(models.Model):
    """One column of the paper Table 8 (HACCP Plan 1.6). Managed by the admin, so a new van is just a new task."""

    name = models.CharField(max_length=80)
    frequency = models.CharField(max_length=10, choices=Frequency.choices, default=Frequency.DAILY)
    active = models.BooleanField(default=True)
    notify = models.BooleanField(
        default=False, help_text='Show a notice and email a reminder when a monthly or quarterly task is due.'
    )
    repeatable = models.BooleanField(
        default=False, help_text='Can be done more than once a day, e.g. stock put away after each delivery.'
    )

    class Meta:
        ordering = ['id']  # the order they were added, which is the order of the paper columns
        constraints = [models.UniqueConstraint(Lower('name'), name='cleaningtask_name_ci_unique')]

    def __str__(self):
        return self.name


class CleaningCheck(Attributed):
    """A task done on a day (one tick on the paper table).

    Never edited or deleted. A tick made by mistake is voided with a reason, which lets it be ticked again."""

    task = models.ForeignKey(CleaningTask, on_delete=models.PROTECT, related_name='checks')
    date = models.DateField()
    number = models.PositiveSmallIntegerField(default=1, help_text='1 for a task done once a day; 1, 2, 3 for one done again.')
    note = models.CharField(max_length=300, blank=True)
    voided = models.BooleanField(default=False)
    void_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['-date', 'task__id']
        constraints = [
            # Each time a task is done that day has its own number, so it cannot be ticked twice by accident.
            # A voided tick frees its number.
            models.UniqueConstraint(fields=['task', 'date', 'number'], condition=Q(voided=False), name='one_live_check_per_task_day_number'),
        ]

    def __str__(self):
        return f'{self.task.name} {self.date:%d/%m/%Y}' + (f' (#{self.number})' if self.number > 1 else '')
