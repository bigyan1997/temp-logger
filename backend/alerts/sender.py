"""Emails the alerts that are due, once each, to everyone on the Alert emails list."""

from setup.models import AlertRecipient

from .checks import due_alerts
from .emails import send_alert_email
from .models import AlertSent


def recipients():
    return list(AlertRecipient.objects.filter(active=True).values_list('email', flat=True))


def send_due_alerts(now):
    """Returns the alerts sent. Nothing is sent (or remembered) while the list is empty, so adding the first
    address later does not trigger a flood. An alert that fails to send is tried again on the next run."""
    to = recipients()
    if not to:
        return []

    sent = []
    for alert in due_alerts(now):
        if AlertSent.objects.filter(kind=alert.kind, key=alert.key).exists():
            continue
        send_alert_email(alert, to)
        AlertSent.objects.create(kind=alert.kind, key=alert.key)
        sent.append(alert)
    return sent
