from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """A permanent note of an important change: who did it, when, what and why.

    Rows are only ever added. The database refuses to change or remove them
    (see migration 0002).
    """

    class Action(models.TextChoices):
        VOIDED = 'voided', 'Entry voided'
        SIGNED_OFF = 'signed_off', 'Corrective action signed off'
        LIMIT_CHANGED = 'limit_changed', 'Temperature limit changed'
        LOGIN_CREATED = 'login_created', 'Login created'
        LOGIN_CHANGED = 'login_changed', 'Login changed'

    at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    action = models.CharField(max_length=20, choices=Action.choices)
    summary = models.CharField(max_length=300)
    reason = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['-at']

    def __str__(self):
        return f'{self.at:%d/%m/%Y %H:%M} {self.summary}'


def record(user, action, summary, reason=''):
    """Add one line to the audit log."""
    return AuditLog.objects.create(user=user, action=action, summary=summary[:300], reason=reason[:300])
