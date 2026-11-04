from django.conf import settings
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class StaffMember(models.Model):
    """A person who takes readings. Picked from a list on every entry, so
    auditors see a real, consistently spelled name even though the app
    logins (admin@ / night@) are shared. Never deleted; deactivate instead."""

    name = models.CharField(max_length=80)
    active = models.BooleanField(default=True)
    both_logins = models.BooleanField(
        default=False, help_text='Offered on the day login as well as the night login.'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(Lower('name'), name='staffmember_name_ci_unique'),
        ]

    def __str__(self):
        return self.name


class Unit(models.Model):
    """A cold or frozen storage unit with its own temperature limit (max, in C)."""

    class Kind(models.TextChoices):
        CHILLED = 'chilled', 'Chilled'
        FROZEN = 'frozen', 'Frozen'

    name = models.CharField(max_length=60)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    max_temp = models.DecimalField(max_digits=4, decimal_places=1)
    active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']
        constraints = [models.UniqueConstraint(Lower('name'), name='unit_name_ci_unique')]

    def __str__(self):
        return self.name


class Supplier(models.Model):
    """A supplier whose deliveries are temperature-checked on receiving (a Table 10 column)."""

    name = models.CharField(max_length=80)
    active = models.BooleanField(default=True)
    # Only sets what Receiving starts on; staff can still change it for a delivery.
    usually_frozen = models.BooleanField(default=False)

    class Meta:
        ordering = ['id']  # the order they were added, which is the order of the paper sheet
        constraints = [models.UniqueConstraint(Lower('name'), name='supplier_name_ci_unique')]

    def __str__(self):
        return self.name


class Run(models.Model):
    """A delivery run (A-E, G, H, J-M). Dispatch temperature is logged per run."""

    code = models.CharField(max_length=10)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']
        constraints = [models.UniqueConstraint(Lower('code'), name='run_code_ci_unique')]

    def __str__(self):
        return f'Run {self.code}'


class AlertRecipient(models.Model):
    """An email address that receives the alerts (reading due, missed, out of limit). Never deleted; deactivate."""

    email = models.EmailField()
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['email']
        constraints = [models.UniqueConstraint(Lower('email'), name='alertrecipient_email_ci_unique')]

    def __str__(self):
        return self.email


class ClosedDay(models.Model):
    """A day with no readings to log, such as a public holiday. Admin-managed in Settings.

    Its daytime storage readings and the evening before are not due (no reminders, shown as closed on the
    screens and PDFs). Its own evening reading still is, because deliveries go out the next morning.
    Receiving and Dispatch are skipped for the whole date. Readings can still be logged on a closed day."""

    date = models.DateField(unique=True)
    label = models.CharField(max_length=60, default='Public holiday')
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'{self.date:%d/%m/%Y} {self.label}'


class Attributed(models.Model):
    """Shared fields for every reading/check: which login saved it and which
    person took it. Add this to StorageReading, ReceivingCheck, DispatchReading."""

    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+',
        help_text='The shared login that saved the entry.',
    )
    recorded_by = models.ForeignKey(
        StaffMember, on_delete=models.PROTECT, related_name='+',
        help_text='The person who took the reading.',
    )
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        abstract = True
