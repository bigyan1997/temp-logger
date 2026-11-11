"""Emails a problem with the system itself (a failed deploy, for example) to SYSTEM_ALERT_EMAIL.

Run by scripts/auto_deploy.ps1 when a deploy fails. With --key the same problem is only emailed once, because the
deploy tries again every 5 minutes. Does nothing (and does not fail) when SYSTEM_ALERT_EMAIL is not set."""

from django.conf import settings
from django.core.management.base import BaseCommand

from alerts.checks import Alert
from alerts.emails import send_alert_email
from alerts.models import AlertSent


class Command(BaseCommand):
    help = 'Email a problem with the system itself (for example a failed deploy) to SYSTEM_ALERT_EMAIL, once per --key.'

    def add_arguments(self, parser):
        parser.add_argument('subject')
        parser.add_argument('message')
        parser.add_argument('--kind', default='system_problem', help='Short name of the kind of problem (max 20 characters)')
        parser.add_argument('--key', default='', help='Identifies this problem (for example a commit), so it is emailed once')

    def handle(self, subject, message, kind, key, **options):
        if not settings.SYSTEM_ALERT_EMAIL:
            self.stdout.write('SYSTEM_ALERT_EMAIL is not set, so nothing was sent.')
            return
        if key and AlertSent.objects.filter(kind=kind, key=key).exists():
            self.stdout.write('Already emailed.')
            return
        send_alert_email(Alert(kind, key, subject, message, lead=message, tone='failed'), [settings.SYSTEM_ALERT_EMAIL])
        if key:
            AlertSent.objects.create(kind=kind, key=key)
        self.stdout.write(f'Sent to {settings.SYSTEM_ALERT_EMAIL}.')
