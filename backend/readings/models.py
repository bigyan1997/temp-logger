import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from setup.models import Attributed, Run, Supplier, Unit

from .choices import Action, ProductType, Status


class Reading(Attributed):
    """Fields shared by every kind of reading.

    Readings are never edited or deleted. A mistake is voided and replaced by a
    corrected row that points back at the original through `supersedes`.
    The id is created by the browser, so a double click or a retry saves once.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    status = models.CharField(max_length=15, choices=Status.choices)
    limit_at_time = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True,
        help_text='The limit this reading was judged against, kept so later limit changes never rewrite history.',
    )
    note = models.CharField(max_length=300, blank=True)
    voided = models.BooleanField(default=False)
    supersedes = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='+')

    class Meta:
        abstract = True


class StorageReading(Reading):
    """One temperature for one unit at one scheduled time (paper Table 9)."""

    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='+')
    slot = models.DateTimeField(help_text='The scheduled reading time this belongs to.')
    value = models.DecimalField(max_digits=4, decimal_places=1)

    class Meta:
        ordering = ['-slot', 'unit__sort_order']
        constraints = [
            models.UniqueConstraint(
                fields=['unit', 'slot'], condition=Q(voided=False), name='one_storage_reading_per_slot'
            ),
        ]

    def __str__(self):
        return f'{self.unit} {self.value} °C at {timezone.localtime(self.slot):%d/%m %H:%M}'


class ReceivingCheck(Reading):
    """A delivery from a supplier, or a note that none arrived (paper Table 10)."""

    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='+')
    date = models.DateField()
    no_delivery = models.BooleanField(default=False)
    temp = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    product_type = models.CharField(max_length=10, choices=ProductType.choices, default=ProductType.CHILLED)
    packaging_ok = models.BooleanField(default=True)

    class Meta:
        ordering = ['-date', 'supplier__name']
        constraints = [
            models.UniqueConstraint(
                fields=['supplier', 'date'], condition=Q(voided=False), name='one_receiving_check_per_supplier_day'
            ),
            models.CheckConstraint(
                condition=Q(no_delivery=False) | Q(temp__isnull=True), name='no_delivery_has_no_temp'
            ),
        ]

    def __str__(self):
        what = 'no delivery' if self.no_delivery else f'{self.temp} °C'
        return f'{self.supplier} {self.date:%d/%m}: {what}'


class DispatchReading(Reading):
    """The temperature of one delivery run's load at dispatch (paper Table 11)."""

    run = models.ForeignKey(Run, on_delete=models.PROTECT, related_name='+')
    date = models.DateField()
    temp = models.DecimalField(max_digits=4, decimal_places=1)

    class Meta:
        ordering = ['-date', 'run__code']
        constraints = [
            models.UniqueConstraint(
                fields=['run', 'date'], condition=Q(voided=False), name='one_dispatch_reading_per_run_day'
            ),
        ]

    def __str__(self):
        return f'{self.run} {self.date:%d/%m}: {self.temp} °C'


class CorrectiveActionQuerySet(models.QuerySet):
    def live(self):
        """Leave out actions that belong to a voided reading: nobody needs to sign those off."""
        return self.exclude(
            Q(storage_reading__voided=True) | Q(receiving_check__voided=True) | Q(dispatch_reading__voided=True)
        )


class CorrectiveAction(models.Model):
    """What was done about a reading that was out of limit. Belongs to exactly one reading."""

    storage_reading = models.OneToOneField(
        StorageReading, null=True, blank=True, on_delete=models.PROTECT, related_name='corrective_action'
    )
    receiving_check = models.OneToOneField(
        ReceivingCheck, null=True, blank=True, on_delete=models.PROTECT, related_name='corrective_action'
    )
    dispatch_reading = models.OneToOneField(
        DispatchReading, null=True, blank=True, on_delete=models.PROTECT, related_name='corrective_action'
    )

    action = models.CharField(max_length=40, choices=Action.choices)
    notes = models.CharField(max_length=500, blank=True)
    hours_above_limit = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True,
        help_text='Storage only: how long the food was above the limit (decides the 2hr/4hr rule).',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    signed_off_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='+'
    )
    signed_off_person = models.ForeignKey(
        'setup.StaffMember', null=True, blank=True, on_delete=models.PROTECT, related_name='+',
        help_text='The person who approved it (the login is shared). Empty on sign-offs made before names were recorded.',
    )
    signed_off_at = models.DateTimeField(null=True, blank=True)
    signed_off_note = models.CharField(
        max_length=500, blank=True,
        help_text='Required when the person signing off also took the reading.',
    )

    objects = CorrectiveActionQuerySet.as_manager()

    class Meta:
        ordering = ['-created_at']
        constraints = [
            # Exactly one of the three links is set.
            models.CheckConstraint(
                name='corrective_action_has_one_reading',
                condition=(
                    Q(storage_reading__isnull=False, receiving_check__isnull=True, dispatch_reading__isnull=True)
                    | Q(storage_reading__isnull=True, receiving_check__isnull=False, dispatch_reading__isnull=True)
                    | Q(storage_reading__isnull=True, receiving_check__isnull=True, dispatch_reading__isnull=False)
                ),
            ),
        ]

    @property
    def signed_off_name(self):
        """Who approved it: the person if we know them, otherwise the login."""
        if self.signed_off_person:
            return self.signed_off_person.name
        return self.signed_off_by.display_name if self.signed_off_by else None

    @property
    def reading(self):
        return self.storage_reading or self.receiving_check or self.dispatch_reading

    def __str__(self):
        return f'{self.get_action_display()} ({self.reading})'
