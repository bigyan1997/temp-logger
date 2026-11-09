import shutil
import tempfile
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase, override_settings

from alerts.models import AlertSent
from alerts.sender import send_due_alerts
from audit.models import AuditLog
from readings.tests.base import ReadingTestCase
from setup.models import AlertRecipient

from . import rules
from .models import Calibration

SYDNEY = ZoneInfo('Australia/Sydney')
FIX = {'action': 'replaced', 'action_notes': 'Bought a new probe.'}


class RuleTests(SimpleTestCase):
    def test_six_months_later_keeps_the_day_or_uses_the_months_last_day(self):
        self.assertEqual(rules.add_months(date(2026, 5, 20), 6), date(2026, 11, 20))
        self.assertEqual(rules.add_months(date(2026, 8, 31), 6), date(2027, 2, 28))
        self.assertEqual(rules.add_months(date(2026, 8, 31), 18), date(2028, 2, 29))
        self.assertEqual(rules.add_months(date(2026, 11, 15), 6), date(2027, 5, 15))

    def test_margin_is_plus_or_minus_one_degree(self):
        from decimal import Decimal
        self.assertTrue(rules.within_margin(Decimal('1.0')))
        self.assertTrue(rules.within_margin(Decimal('-1.0')))
        self.assertFalse(rules.within_margin(Decimal('1.1')))
        self.assertFalse(rules.within_margin(Decimal('-1.1')))

    def test_due_state_follows_the_fifteen_day_notice(self):
        last = date(2026, 5, 20)  # due 20 November
        state = lambda today: rules.due_state(last, today)['state']
        self.assertEqual(state(date(2026, 11, 4)), 'ok')         # 16 days left
        self.assertEqual(state(date(2026, 11, 5)), 'due_soon')   # 15 days left
        self.assertEqual(state(date(2026, 11, 20)), 'due_soon')  # due today
        self.assertEqual(state(date(2026, 11, 21)), 'overdue')
        self.assertEqual(rules.due_state(None, date(2026, 11, 5))['state'], 'never')


class CalibrationApiTests(ReadingTestCase):
    def setUp(self):
        super().setUp()
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder, ignore_errors=True)
        override = override_settings(REPORTS_LOCAL_DIR=self.folder, REPORTS_EXPORT_DIR='', GOOGLE_DRIVE_FOLDER_ID='')
        override.enable()
        self.addCleanup(override.disable)
        self.sign_in(self.admin)

    def calibrate(self, reading='0.5', day='2026-11-02', gauges=None, **extra):
        return self.post('/api/calibrations/', date=day, probe_reading=reading, gauges=gauges or [], **extra)

    def gauge(self, unit, gauge='3.0', probe='3.2', comment=''):
        return {'unit': unit.pk, 'gauge_reading': gauge, 'probe_reading': probe, 'comment': comment}

    # Who may use it ---------------------------------------------------------

    def test_only_day_staff_can_use_it(self):
        self.sign_in(self.night)
        self.assertEqual(self.client.get('/api/calibrations/').status_code, 403)
        self.assertEqual(self.calibrate().status_code, 403)

    # Saving -----------------------------------------------------------------

    def test_a_good_calibration_saves_with_its_gauge_checks(self):
        response = self.calibrate(
            gauges=[self.gauge(self.coolroom), self.gauge(self.freezer, '-17.0', '-18.4', 'Gauge reads warm')]
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['passed'])
        self.assertEqual(data['probe_difference'], '0.5')
        self.assertEqual([g['unit_name'] for g in data['gauges']], ['Coolroom', 'Freezer'])
        self.assertEqual(data['gauges'][1]['difference'], '1.4')  # the freezer gauge is 1.4 above the probe
        self.assertEqual(data['recorded_by_name'], 'Sam')

    def test_exactly_one_degree_out_still_passes_and_more_fails(self):
        self.assertTrue(self.calibrate('1.0').json()['passed'])
        self.assertTrue(self.calibrate('-1.0', day='2026-11-03').json()['passed'])
        response = self.calibrate('1.1', day='2026-11-04')
        self.assertEqual(response.status_code, 400)  # failed, and no action was given

    def test_a_failed_probe_needs_an_action_and_a_note(self):
        self.assertIn('action', self.calibrate('2.0').json())
        self.assertIn('action_notes', self.calibrate('2.0', action='replaced').json())
        response = self.calibrate('2.0', **FIX)
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.json()['passed'])
        self.assertEqual(response.json()['action_label'], 'Thermometer replaced')

    def test_a_gauge_more_than_a_degree_out_needs_a_comment(self):
        bad = self.gauge(self.coolroom, '5.0', '3.0')
        self.assertEqual(self.calibrate(gauges=[bad]).status_code, 400)
        bad['comment'] = 'Gauge reads high. Booked a service.'
        self.assertEqual(self.calibrate(gauges=[bad]).status_code, 201)

    def test_refuses_future_dates_and_the_same_unit_twice(self):
        self.assertEqual(self.calibrate(day='2999-01-01').status_code, 400)
        twice = [self.gauge(self.coolroom), self.gauge(self.coolroom)]
        self.assertEqual(self.calibrate(gauges=twice).status_code, 400)

    def test_saving_twice_with_the_same_id_keeps_one(self):
        entry = '8c4d5b5a-4c2a-4bde-9b53-5f6f1d6f0a11'
        self.assertEqual(self.calibrate(id=entry).status_code, 201)
        self.assertEqual(self.calibrate(id=entry).status_code, 200)
        self.assertEqual(Calibration.objects.count(), 1)

    # PDF and copies -----------------------------------------------------------

    def test_saving_makes_a_pdf_copy_in_the_report_exports_folder(self):
        data = self.calibrate(gauges=[self.gauge(self.coolroom)]).json()
        files = list((self.folder / 'calibration').glob('*.pdf'))
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].read_bytes().startswith(b'%PDF'))
        self.assertEqual(data['copies']['problems'], [])

    def test_the_pdf_can_be_downloaded_again(self):
        entry = self.calibrate(**FIX, reading='2.5', gauges=[self.gauge(self.coolroom, '5.0', '3.0', 'Gauge reads high')]).json()
        response = self.client.get(f'/api/calibrations/{entry["id"]}/pdf/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_a_drive_problem_does_not_lose_the_calibration(self):
        with override_settings(REPORTS_EXPORT_DIR=str(self.folder / 'no-such-drive')):
            response = self.calibrate()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Calibration.objects.count(), 1)
        self.assertTrue(response.json()['copies']['problems'])
        self.assertEqual(len(response.json()['copies']['saved']), 1)  # the copy on this PC still worked

    # Voiding ----------------------------------------------------------------

    def test_voiding_needs_a_reason_and_is_written_to_the_audit_log(self):
        entry = self.calibrate().json()
        self.assertEqual(self.client.post(f'/api/calibrations/{entry["id"]}/void/', {}, format='json').status_code, 400)
        response = self.client.post(f'/api/calibrations/{entry["id"]}/void/', {'reason': 'Wrong day'}, format='json')
        self.assertTrue(response.json()['voided'])
        self.assertTrue(AuditLog.objects.filter(action='voided', reason='Wrong day').exists())
        self.assertEqual(self.client.get('/api/calibrations/').json()['count'], 0)
        self.assertEqual(self.client.get('/api/calibrations/?include_voided=1').json()['count'], 1)

    def test_a_voided_calibration_pdf_still_opens_and_cannot_be_voided_twice(self):
        entry = self.calibrate().json()
        self.client.post(f'/api/calibrations/{entry["id"]}/void/', {'reason': 'Wrong day'}, format='json')
        self.assertEqual(self.client.get(f'/api/calibrations/{entry["id"]}/pdf/').status_code, 200)
        self.assertEqual(self.client.post(f'/api/calibrations/{entry["id"]}/void/', {'reason': 'Again'}, format='json').status_code, 400)

    # When it is next due --------------------------------------------------------

    def due(self):
        return self.client.get('/api/calibrations/due/').json()

    def test_due_date_is_six_months_after_the_last_pass(self):
        self.assertEqual(self.due()['state'], 'never')
        self.calibrate(day='2026-05-20')
        self.assertEqual(self.due()['due'], '2026-11-20')

    def test_a_failed_or_voided_calibration_does_not_reset_the_clock(self):
        self.calibrate(day='2026-05-20')
        self.calibrate('3.0', day='2026-10-01', **FIX)
        voided = self.calibrate(day='2026-10-02').json()
        self.client.post(f'/api/calibrations/{voided["id"]}/void/', {'reason': 'Mistake'}, format='json')
        self.assertEqual(self.due()['due'], '2026-11-20')


class CalibrationAlertTests(ReadingTestCase):
    def setUp(self):
        super().setUp()
        AlertRecipient.objects.create(email='boss@example.com')
        self.sign_in(self.admin)
        override = override_settings(REPORTS_LOCAL_DIR=Path(tempfile.mkdtemp()), REPORTS_EXPORT_DIR='', GOOGLE_DRIVE_FOLDER_ID='')
        override.enable()
        self.addCleanup(override.disable)
        self.post('/api/calibrations/', date='2026-05-20', probe_reading='0.0', gauges=[])  # next due 20 Nov

    def kinds(self, day, hour=9):
        return [alert.kind for alert in send_due_alerts(datetime(2026, 11, day, hour, tzinfo=SYDNEY)) if alert.kind.startswith('calibration')]

    def test_the_notice_starts_fifteen_days_before_and_is_sent_once(self):
        self.assertEqual(self.kinds(4), [])
        self.assertEqual(self.kinds(5), ['calibration'])
        self.assertEqual(self.kinds(5, hour=10), [])  # not again the same day
        self.assertEqual(self.kinds(6), [])           # nor on later days
        self.assertEqual(AlertSent.objects.filter(kind='calibration').count(), 1)

    def test_an_overdue_email_is_sent_once_after_the_due_date(self):
        self.assertEqual(self.kinds(21), ['calibration_overdue'])
        self.assertEqual(self.kinds(22), [])

    def test_nothing_is_sent_before_any_calibration_exists(self):
        Calibration.objects.all().delete()
        self.assertEqual(self.kinds(21), [])
