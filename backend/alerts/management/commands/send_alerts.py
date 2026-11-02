"""Emails any alerts that are due. Run every 5 minutes by a scheduled task (scripts/install_autostart.ps1)."""

from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from alerts.sender import recipients, send_due_alerts


class Command(BaseCommand):
    help = 'Email the alerts that are due (reading almost due, missed, out of limit, waiting for sign-off).'

    def add_arguments(self, parser):
        parser.add_argument('--test', action='store_true', help='Send one test email to the Alert emails list')

    def handle(self, test, **options):
        if test:
            to = recipients()
            if not to:
                raise CommandError('No one is on the Alert emails list. Add an address under Settings first.')
            send_mail('[Temperature Logger] Test alert', 'Alert emails are working.', None, to)
            self.stdout.write(f'Test email sent to {", ".join(to)}.')
            return
        sent = send_due_alerts(timezone.now())
        for alert in sent:
            self.stdout.write(f'Sent: {alert.subject}')
        self.stdout.write(f'Done: {len(sent)} alert(s).')
