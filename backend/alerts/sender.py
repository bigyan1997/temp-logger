"""Emails the alerts that are due, once each, to everyone on the Alert emails list."""

from django.conf import settings

from setup.models import AlertRecipient

from .checks import due_alerts
from .emails import MODULES, module_for, send_alert_email
from .models import AlertSent


def recipients():
    return list(AlertRecipient.objects.filter(active=True).values_list('email', flat=True))


def recipients_for(alert):
    """Problems with the system itself (a failed backup) go to SYSTEM_ALERT_EMAIL when it is set; everything else goes
    to the Alert emails list."""
    if module_for(alert.kind) is MODULES['system'] and settings.SYSTEM_ALERT_EMAIL:
        return [settings.SYSTEM_ALERT_EMAIL]
    return recipients()


def send_due_alerts(now):
    """Returns the alerts sent. An alert with no one to send to is neither sent nor remembered, so adding the first
    address later does not trigger a flood. An alert that fails to send is tried again on the next run."""
    sent = []
    for alert in due_alerts(now):
        if AlertSent.objects.filter(kind=alert.kind, key=alert.key).exists():
            continue
        to = recipients_for(alert)
        if not to:
            continue
        send_alert_email(alert, to)
        AlertSent.objects.create(kind=alert.kind, key=alert.key)
        sent.append(alert)
    return sent
