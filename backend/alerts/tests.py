import os
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from alerts.emails import module_for, render_html
from alerts.models import AlertSent
from alerts.sender import send_due_alerts
from readings.tests.base import MONDAY_9AM, MONDAY_9PM, ReadingTestCase
from setup.models import AlertRecipient, Unit

SYDNEY = ZoneInfo('Australia/Sydney')
FIX = {'action': 'discarded', 'notes': 'Done'}
FRIDAY_3PM = '2026-11-06T15:00:00+11:00'


def at(day, hour, minute=0):
    """A Sydney time in November 2026 (Monday 2 Nov is day 2)."""
    return datetime(2026, 11, day, hour, minute, tzinfo=SYDNEY)


def monday(hour, minute=0):
    return at(2, hour, minute)


class AlertTests(ReadingTestCase):
    def setUp(self):
        super().setUp()
        AlertRecipient.objects.create(email='boss@example.com')
        self.sign_in(self.night)

    def subjects(self):
        return [message.subject for message in mail.outbox]

    def kinds(self, now):
        return [alert.kind for alert in send_due_alerts(now)]

    def log_everything(self, slot):
        for unit in Unit.objects.filter(active=True):
            self.storage(unit, '-18.0' if unit.kind == 'frozen' else '3.0', slot=slot)

    # The day reading (9 am): reminders at 8:30 am and 12 pm ---------------------

    def test_first_reminder_at_8_30_am_lists_the_unlogged_units(self):
        self.assertEqual(self.kinds(monday(8, 29)), [])
        self.assertEqual(self.kinds(monday(8, 30)), ['reminder'])
        self.assertIn('9:00 AM', self.subjects()[0])
        self.assertIn('Coolroom', mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, ['boss@example.com'])

    def test_second_reminder_at_12_pm_if_still_not_logged(self):
        self.assertEqual(self.kinds(monday(11, 59)), [])
        self.assertEqual(self.kinds(monday(12, 0)), ['reminder2'])
        self.assertIn('STILL NOT LOGGED', self.subjects()[0])

    def test_no_second_reminder_when_it_was_logged_in_between(self):
        self.kinds(monday(8, 30))
        self.log_everything(MONDAY_9AM)
        self.assertEqual(self.kinds(monday(12, 0)), [])
        self.assertEqual(len(mail.outbox), 1)

    def test_no_reminder_when_everything_is_already_logged(self):
        self.log_everything(MONDAY_9AM)
        self.assertEqual(self.kinds(monday(8, 30)), [])

    def test_a_reminder_only_lists_the_units_still_missing(self):
        self.storage(self.coolroom, '3.0', slot=MONDAY_9AM)
        self.kinds(monday(8, 30))
        self.assertIn('Freezer', mail.outbox[0].body)
        self.assertNotIn('Still to log: Coolroom', mail.outbox[0].body)

    # The night reading (9 pm): reminders at 8:30 pm and 12 am -----------------------

    def test_night_reminders_at_8_30_pm_and_midnight(self):
        self.assertEqual(self.kinds(monday(20, 30)), ['reminder'])
        self.assertIn('9:00 PM', self.subjects()[0])
        self.assertEqual(self.kinds(at(3, 0, 0)), ['reminder2'])  # 12 am Tuesday, about Monday's 9 pm reading
        self.assertIn('Monday', mail.outbox[1].body)

    def test_no_midnight_reminder_when_the_night_reading_was_logged(self):
        self.log_everything(MONDAY_9PM)
        self.assertEqual(self.kinds(at(3, 0, 0)), [])

    # Friday's 3 pm reading: 2:30 pm and 6 pm -----------------------------------

    def test_friday_afternoon_reading_reminders(self):
        self.assertEqual(self.kinds(at(6, 14, 30)), ['reminder'])
        self.assertIn('3:00 PM', self.subjects()[0])
        self.assertEqual(self.kinds(at(6, 18, 0)), ['reminder2'])

    def test_friday_afternoon_reading_logged_means_no_reminders(self):
        self.log_everything(FRIDAY_3PM)
        self.assertEqual(self.kinds(at(6, 14, 30)), [])
        self.assertEqual(self.kinds(at(6, 18, 0)), [])

    # Not repeated, not sent to nobody ---------------------------------------------

    def test_the_same_alert_is_only_sent_once(self):
        self.kinds(monday(8, 30))
        self.kinds(monday(8, 35))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(AlertSent.objects.count(), 1)

    def test_a_late_second_reminder_is_not_sent_hours_after(self):
        self.assertEqual(self.kinds(monday(14, 0)), [])

    def test_nothing_is_sent_or_remembered_with_nobody_on_the_list(self):
        AlertRecipient.objects.update(active=False)
        self.assertEqual(self.kinds(monday(8, 30)), [])
        self.assertEqual(AlertSent.objects.count(), 0)

    def test_out_of_limit_readings_and_unsigned_actions_send_no_email(self):
        self.dispatch('7.5', corrective=FIX)
        self.assertEqual(self.kinds(monday(10)), [])  # between the 8:30 and 12:00 reminders

    # The test commands ---------------------------------------------------------------------

    def test_demo_sends_one_of_every_alert_without_recording_anything(self):
        call_command('send_alerts', demo=True)
        self.assertEqual(len(mail.outbox), 2)
        self.assertTrue(all('TEST' in subject for subject in self.subjects()))
        self.assertEqual(AlertSent.objects.count(), 0)

    def test_emails_have_a_styled_html_version_with_the_units(self):
        self.kinds(monday(8, 30))
        message = mail.outbox[0]
        html, kind = message.alternatives[0]
        self.assertEqual(kind, 'text/html')
        self.assertIn('DUE SOON', html)
        self.assertIn('Not logged', html)
        self.assertIn('Freezer', html)
        self.assertIn('Still to log', message.body)  # the plain text version is still there

    def test_the_second_reminder_looks_more_urgent(self):
        self.kinds(monday(12, 0))
        self.assertIn('STILL NOT LOGGED', mail.outbox[0].alternatives[0][0])

    def test_the_button_links_to_the_app_when_its_address_is_set(self):
        with self.settings(APP_URL='http://example.test:8003/'):
            self.kinds(monday(8, 30))
        self.assertIn('http://example.test:8003/log/storage', mail.outbox[0].alternatives[0][0])

    def test_no_button_without_an_app_address(self):
        with self.settings(APP_URL=''):
            self.kinds(monday(8, 30))
        self.assertNotIn('Open the Temperature Logger', mail.outbox[0].alternatives[0][0])

    def test_test_email_command(self):
        call_command('send_alerts', test=True)
        self.assertEqual(self.subjects(), ['Achieve HACCP: Test alert'])
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


class BackupAlertTests(ReadingTestCase):
    """The 'backup failed' email: sent from 6 am when today has no good backup in BACKUP_DIR."""

    def setUp(self):
        super().setUp()
        AlertRecipient.objects.create(email='boss@example.com')
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder, ignore_errors=True)
        override = override_settings(BACKUP_DIR=str(self.folder))
        override.enable()
        self.addCleanup(override.disable)

    def dump(self, day, size=5000):
        path = self.folder / f'temp_logger_2026-11-{day:02d}.dump'
        path.write_bytes(b'x' * size)
        stamp = at(day, 2).timestamp()
        os.utime(path, (stamp, stamp))

    def kinds(self, now):
        return [alert.kind for alert in send_due_alerts(now)]

    def test_no_alert_when_todays_backup_exists(self):
        self.dump(3)
        self.assertEqual(self.kinds(at(3, 7)), [])

    def test_alert_when_there_is_no_backup_today(self):
        self.dump(2)
        self.assertEqual(self.kinds(at(3, 7)), ['backup'])
        self.assertIn('BACKUP FAILED', mail.outbox[0].subject)
        self.assertIn('Monday 02 November 2026', mail.outbox[0].body)

    def test_no_alert_before_6_am(self):
        self.assertEqual(self.kinds(at(3, 5, 55)), [])

    def test_a_tiny_dump_does_not_count(self):
        self.dump(3, size=100)
        self.assertEqual(self.kinds(at(3, 7)), ['backup'])

    def test_alert_when_the_folder_is_missing(self):
        shutil.rmtree(self.folder)
        self.assertEqual(self.kinds(at(3, 7)), ['backup'])
        self.assertIn('No backup has been found', mail.outbox[0].body)

    def test_only_one_alert_per_day(self):
        self.assertEqual(self.kinds(at(3, 7)), ['backup'])
        self.assertEqual(self.kinds(at(3, 7, 5)), [])
        self.assertEqual(self.kinds(at(4, 7)), ['backup'])

    @override_settings(BACKUP_DIR='')
    def test_not_checked_when_backup_dir_is_not_set(self):
        self.assertEqual(self.kinds(at(3, 7)), [])


class EmailLookTests(SimpleTestCase):
    """Each part of the app has its own name, icon, colour and button in its emails."""

    def test_each_kind_of_alert_belongs_to_the_right_module(self):
        names = {kind: module_for(kind)['name'] for kind in ('reminder', 'out_of_limit', 'cleaning_due', 'cleaning_late', 'calibration', 'calibration_overdue', 'backup', 'test')}
        self.assertEqual(names['reminder'], 'Temperature Logger')
        self.assertEqual(names['cleaning_due'], 'Cleaning & Maintenance')
        self.assertEqual(names['cleaning_late'], 'Cleaning & Maintenance')
        self.assertEqual(names['calibration'], 'Calibration')
        self.assertEqual(names['calibration_overdue'], 'Calibration')
        self.assertEqual(names['backup'], 'Achieve HACCP')
        self.assertEqual(names['test'], 'Achieve HACCP')

    def test_the_cleaning_email_is_not_headed_temperature_logger(self):
        with override_settings(APP_URL='http://orders-pc:8003'):
            html = render_html('OVERDUE: Pest spray (quarterly)', 'It was due.', (), 'failed', module_for('cleaning_late'))
        self.assertIn('Cleaning &amp; Maintenance', html)
        self.assertIn('Open Notifications', html)
        self.assertIn('http://orders-pc:8003/cleaning/notifications', html)
        self.assertNotIn('Temperature Logger', html)
