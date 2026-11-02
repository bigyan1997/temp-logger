from django.db import models


class AlertSent(models.Model):
    """One email already sent, so the same alert is never sent twice. `key` says which thing it was about."""

    kind = models.CharField(max_length=20)
    key = models.CharField(max_length=80)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['kind', 'key'], name='alertsent_kind_key_unique')]

    def __str__(self):
        return f'{self.kind} {self.key}'
