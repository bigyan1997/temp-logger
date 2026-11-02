from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError

from alerts.models import AlertSent
from alerts.sender import send_due_alerts
from readings.tests.base import MONDAY_9AM, ReadingTestCase
from setup.models import AlertRecipient, Unit

SYDNEY = ZoneInfo('Australia/Sydney')
FIX = {'action': 'discarded'}


def monday(hour, minute=0):
    return datetime(2026, 11, 2, hour, minute, tzinfo=SYDNEY)


class AlertTests(ReadingTestCase):
    def setUp(self):
        super().setUp()
        AlertRecipient.objects.create(email='boss@example.com')
        self.sign_in(self.night)

    def subjects(self):
        return [message.subject for message in mail.outbox]

    def test_reminder_15_minutes_before_a_slot_lists_the_unlogged_units(self):
        sent = send_due_alerts(monday(8, 46))
        self.assertEqual([a.kind for a in sent], ['reminder'])
        self.assertIn('9:00 AM', self.subjects()[0])
        self.assertIn('Coolroom', mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, ['boss@example.com'])

    def test_no_reminder_too_early_or_once_everything_is_logged(self):
        self.assertEqual(send_due_alerts(monday(8, 30)), [])
        for unit in Unit.objects.filter(active=True):
            self.storage(unit, '-18.0' if unit.kind == 'frozen' else '3.0', slot=MONDAY_9AM)
        self.assertEqual(send_due_alerts(monday(8, 50)), [])

    def test_the_same_alert_is_only_sent_once(self):
        send_due_alerts(monday(8, 46))
        send_due_alerts(monday(8, 51))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(AlertSent.objects.count(), 1)

    def test_missed_after_the_grace_period(self):
        self.assertEqual([a.kind for a in send_due_alerts(monday(10, 30))], [])
        sent = send_due_alerts(monday(11, 5))
        self.assertEqual([a.kind for a in sent], ['missed'])
        self.assertIn('MISSED', self.subjects()[0])

    def test_out_of_limit_reading_is_emailed_with_the_action(self):
        self.dispatch('7.5', corrective=FIX)
        sent = send_due_alerts(datetime.now(SYDNEY))
        self.assertIn('out_of_limit', [a.kind for a in sent])
        body = next(m.body for m in mail.outbox if 'OUT OF LIMIT' in m.subject)
        self.assertIn('Sam', body)
        self.assertIn('Action taken', body)

    def test_a_corrective_action_nobody_signed_off_is_chased_after_two_hours(self):
        self.dispatch('7.5', corrective=FIX)
        soon = datetime.now(SYDNEY) + timedelta(hours=2, minutes=1)
        self.assertIn('sign_off', [a.kind for a in send_due_alerts(soon)])

    def test_nothing_is_sent_or_remembered_with_nobody_on_the_list(self):
        AlertRecipient.objects.update(active=False)
        self.assertEqual(send_due_alerts(monday(8, 46)), [])
        self.assertEqual(AlertSent.objects.count(), 0)

    def test_test_email_command(self):
        call_command('send_alerts', test=True)
        self.assertEqual(self.subjects(), ['[Temperature Logger] Test alert'])
        AlertRecipient.objects.update(active=False)
        with self.assertRaises(CommandError):
            call_command('send_alerts', test=True)


class AlertRecipientApiTests(ReadingTestCase):
    def test_only_admin_can_see_or_change_the_list(self):
        self.sign_in(self.night)
        self.assertEqual(self.client.get('/api/alert-recipients/').status_code, 403)
        self.sign_in(self.admin)
        created = self.client.post('/api/alert-recipients/', {'email': 'boss@example.com'}, format='json')
        self.assertEqual(created.status_code, 201)
        again = self.client.post('/api/alert-recipients/', {'email': 'BOSS@example.com'}, format='json')
        self.assertEqual(again.status_code, 400)  # the same address, ignoring capitals
        self.assertEqual(len(self.client.get('/api/alert-recipients/').json()), 1)
