import uuid

from django.db import models

from setup.models import Attributed, Unit


class Action(models.TextChoices):
    """What was done when the thermometer was outside the margin of error (HACCP Table 14)."""

    REPLACED = 'replaced', 'Thermometer replaced'
    REPAIRED = 'repaired', 'Thermometer repaired'


class Calibration(Attributed):
    """One sitting of the paper Table 14: the probe thermometer's ice-point check, plus any gauge checks.

    Never edited or deleted. A mistake is voided with a reason, and the check is done again."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)  # made by the browser, so a retry saves once
    date = models.DateField()
    probe_reading = models.DecimalField(max_digits=4, decimal_places=1, help_text='What the probe read in iced water. It should be 0.')
    probe_comment = models.CharField(max_length=300, blank=True)
    passed = models.BooleanField(help_text='Within the margin of error, judged when it was saved.')
    action = models.CharField(max_length=20, choices=Action.choices, blank=True)
    action_notes = models.CharField(max_length=500, blank=True)
    voided = models.BooleanField(default=False)
    void_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['-date', '-recorded_at']

    def __str__(self):
        return f'Thermometer calibration {self.date:%d/%m/%Y}: {self.probe_reading} °C'


class GaugeCheck(models.Model):
    """A coolroom or freezer's own gauge compared with the calibrated probe, as part of one calibration."""

    calibration = models.ForeignKey(Calibration, on_delete=models.PROTECT, related_name='gauges')
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='+')
    gauge_reading = models.DecimalField(max_digits=4, decimal_places=1, help_text="What the unit's own gauge shows.")
    probe_reading = models.DecimalField(max_digits=4, decimal_places=1, help_text='What the calibrated probe reads in the unit.')
    comment = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['unit__sort_order']
        constraints = [models.UniqueConstraint(fields=['calibration', 'unit'], name='one_gauge_check_per_unit')]

    @property
    def difference(self):
        return self.gauge_reading - self.probe_reading
