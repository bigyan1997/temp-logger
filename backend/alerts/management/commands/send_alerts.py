"""Emails any alerts that are due. Run every 5 minutes by a scheduled task (scripts/install_autostart.ps1)."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from alerts.checks import sample_alerts, test_alert
from alerts.emails import send_alert_email
from alerts.sender import recipients, send_due_alerts
from nonconformance.drive import copy_pending


class Command(BaseCommand):
    help = 'Email the alerts that are due (reading almost due, missed, out of limit).'

    def add_arguments(self, parser):
        parser.add_argument('--test', action='store_true', help='Send one test email to the Alert emails list')
        parser.add_argument('--test-system', action='store_true', help='Send one test email to SYSTEM_ALERT_EMAIL (failed backups and deploys)')
        parser.add_argument('--demo', action='store_true', help='Send one made-up example of every alert to the list')

    def handle(self, test, demo, test_system, **options):
        if test_system:
            if not settings.SYSTEM_ALERT_EMAIL:
                raise CommandError('SYSTEM_ALERT_EMAIL is not set in backend\\.env.')
            send_alert_email(test_alert(), [settings.SYSTEM_ALERT_EMAIL])
            self.stdout.write(f'Test email sent to {settings.SYSTEM_ALERT_EMAIL}.')
            return
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
        # This task runs every 5 minutes, so it also retries any report photo that is not in Google Drive yet.
        try:
            copied = copy_pending()
            if copied:
                self.stdout.write(f'Copied {copied} report photo(s) to Google Drive.')
        except Exception as problem:  # never let this stop the alerts
            self.stdout.write(f'Report photo copy failed: {problem}')
