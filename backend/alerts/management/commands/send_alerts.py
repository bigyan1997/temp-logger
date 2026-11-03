"""Emails any alerts that are due. Run every 5 minutes by a scheduled task (scripts/install_autostart.ps1)."""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from alerts.checks import sample_alerts, test_alert
from alerts.emails import send_alert_email
from alerts.sender import recipients, send_due_alerts


class Command(BaseCommand):
    help = 'Email the alerts that are due (reading almost due, missed, out of limit).'

    def add_arguments(self, parser):
        parser.add_argument('--test', action='store_true', help='Send one test email to the Alert emails list')
        parser.add_argument('--demo', action='store_true', help='Send one made-up example of every alert to the list')

    def handle(self, test, demo, **options):
        if demo:
            to = recipients()
            if not to:
                raise CommandError('No one is on the Alert emails list. Add an address under Settings first.')
            for alert in sample_alerts():
                send_alert_email(alert, to)
                self.stdout.write(f'Sent: {alert.subject}')
            return
        if test:
            to = recipients()
            if not to:
                raise CommandError('No one is on the Alert emails list. Add an address under Settings first.')
            send_alert_email(test_alert(), to)
            self.stdout.write(f'Test email sent to {", ".join(to)}.')
            return
        sent = send_due_alerts(timezone.now())
        for alert in sent:
            self.stdout.write(f'Sent: {alert.subject}')
        self.stdout.write(f'Done: {len(sent)} alert(s).')
