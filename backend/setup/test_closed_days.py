"""Closed days (public holidays): the rule, the Settings list, and where they show up."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.core import mail

from alerts.sender import send_due_alerts
from audit.models import AuditLog
from readings.dashboard import build_dashboard, missed_storage_slots
from readings.day import build_day
from readings.schedule import slots_on
from readings.tests.base import ReadingTestCase
from reports.grids import dispatch_grid, receiving_grid, storage_sheets
from setup.closed_days import day_closure, storage_closure
from setup.models import AlertRecipient, ClosedDay

SYDNEY = ZoneInfo('Australia/Sydney')
MONDAY = date(2026, 11, 2)  # the holiday in these tests


def at(day, hour, minute=0):
    return datetime(2026, 11, day, hour, minute, tzinfo=SYDNEY)


class ClosedDayTestCase(ReadingTestCase):
    def setUp(self):
        super().setUp()
        ClosedDay.objects.create(date=MONDAY, label='Public holiday')


class ClosedDayRuleTests(ClosedDayTestCase):
    def test_sunday_night_and_monday_morning_are_closed_but_monday_night_is_not(self):
        self.assertEqual(storage_closure(at(1, 21)), 'Public holiday')  # Sunday 9 pm: the night before
        self.assertEqual(storage_closure(at(2, 9)), 'Public holiday')
        self.assertIsNone(storage_closure(at(2, 21)))  # deliveries go out Tuesday morning
        self.assertIsNone(storage_closure(at(3, 9)))

    def test_a_friday_holiday_skips_everything_that_day_and_thursday_night(self):
        friday = date(2026, 11, 6)
        self.assertIsNone(day_closure(friday))  # an ordinary Friday is normal
        self.assertIsNone(storage_closure(at(6, 15)))
        ClosedDay.objects.create(date=friday, label='Public holiday')
        self.assertEqual(storage_closure(at(5, 21)), 'Public holiday')  # Thursday 9 pm: nobody is in
        self.assertEqual(storage_closure(at(6, 9)), 'Public holiday')
        self.assertEqual(storage_closure(at(6, 15)), 'Public holiday')  # Friday 3 pm
        self.assertEqual(day_closure(friday), 'Public holiday')

    def test_receiving_and_dispatch_are_skipped_for_the_date_only(self):
        self.assertEqual(day_closure(MONDAY), 'Public holiday')
        self.assertIsNone(day_closure(date(2026, 11, 1)))
        self.assertIsNone(day_closure(date(2026, 11, 3)))

    def test_a_deactivated_closed_day_is_ignored(self):
        ClosedDay.objects.update(active=False)
        self.assertIsNone(storage_closure(at(2, 9)))


class ClosedDayListTests(ReadingTestCase):
    def test_admin_adds_edits_and_deletes_with_audit_entries(self):
        self.sign_in(self.admin)
        created = self.client.post('/api/closed-days/', {'date': '2026-12-25', 'label': ''}, format='json')
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()['label'], 'Public holiday')  # blank means the usual label
        url = f'/api/closed-days/{created.json()["id"]}/'
        self.assertEqual(self.client.patch(url, {'label': 'Christmas Day'}, format='json').status_code, 200)
        self.assertEqual(self.client.delete(url).status_code, 204)
        actions = list(AuditLog.objects.order_by('id').values_list('action', flat=True))
        self.assertEqual(actions, ['closed_day', 'closed_day', 'deleted'])

    def test_the_same_day_cannot_be_added_twice(self):
        self.sign_in(self.admin)
        self.client.post('/api/closed-days/', {'date': '2026-12-25'}, format='json')
        again = self.client.post('/api/closed-days/', {'date': '2026-12-25'}, format='json')
        self.assertEqual(again.status_code, 400)

    def test_night_login_can_read_but_not_change(self):
        ClosedDay.objects.create(date=date(2026, 12, 25))
        self.sign_in(self.night)
        self.assertEqual(len(self.client.get('/api/closed-days/').json()), 1)
        self.assertEqual(self.client.post('/api/closed-days/', {'date': '2026-12-26'}, format='json').status_code, 403)


class ClosedDayEffectTests(ClosedDayTestCase):
    def setUp(self):
        super().setUp()
        AlertRecipient.objects.create(email='boss@example.com')
        self.sign_in(self.night)

    def test_no_reminders_for_closed_readings_but_monday_night_still_gets_them(self):
        self.assertEqual(send_due_alerts(at(2, 8, 30)), [])   # Monday 9 am
        self.assertEqual(send_due_alerts(at(1, 20, 30)), [])  # Sunday 9 pm
        self.assertEqual([a.kind for a in send_due_alerts(at(2, 20, 30))], ['reminder'])  # Monday 9 pm
        self.assertEqual(len(mail.outbox), 1)

    def test_closed_readings_are_not_missed_on_the_dashboard(self):
        slots = [m['slot'] for m in missed_storage_slots(at(3, 12))]
        self.assertNotIn(at(2, 9), slots)
        self.assertIn(at(2, 21), slots)
        self.assertEqual(build_dashboard(at(2, 12))['tiles']['missed'], 0)

    def test_the_day_screen_marks_closed_times(self):
        day = build_day(MONDAY, at(2, 10))
        states = {s['slot'].hour: (s['state'], s['closed']) for s in day['storage']}
        self.assertEqual(states[9], ('closed', 'Public holiday'))
        self.assertEqual(states[21], ('upcoming', None))
        self.assertEqual(day['closed'], 'Public holiday')
        self.assertIsNone(build_day(date(2026, 11, 3), at(3, 10))['closed'])

    def test_a_reading_can_still_be_logged_on_a_closed_day(self):
        self.assertEqual(self.storage(self.coolroom, '3.0').status_code, 201)

    def test_reports_say_public_holiday_where_nothing_was_logged(self):
        monday = next(r for r in receiving_grid(date(2026, 11, 2), date(2026, 11, 6))['rows'] if r['day'] == 'Monday')
        self.assertEqual(monday['closed'], 'Public holiday')
        self.assertEqual(dispatch_grid(date(2026, 11, 2), date(2026, 11, 6))['rows'][0]['closed'], 'Public holiday')

        rows = storage_sheets(date(2026, 11, 2), date(2026, 11, 6))[0]['rows']
        times = [r for r in rows if r['kind'] == 'time']
        # Sunday 9 pm, Monday 9 am closed; Monday 9 pm and Tuesday 9 am open.
        self.assertEqual([r['closed'][0] for r in times[:4]], ['Public holiday', 'Public holiday', None, None])

    def test_a_reading_logged_anyway_shows_instead_of_the_label(self):
        self.dispatch('4.0', date='2026-11-02')
        self.assertIsNone(dispatch_grid(date(2026, 11, 2), date(2026, 11, 6))['rows'][0]['closed'])

    def test_the_pdfs_still_build_with_a_public_holiday_in_them(self):
        self.sign_in(self.admin)
        for kind in ('storage', 'receiving', 'dispatch'):
            response = self.client.get(f'/api/reports/{kind}.pdf?from=2026-11-02&to=2026-11-08')
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.content.startswith(b'%PDF'))


class AfternoonBeforeAHolidayTests(ReadingTestCase):
    """Friday 6 Nov is a holiday, so Thursday 5 Nov takes its reading at 3 pm instead of 9 pm."""

    def setUp(self):
        super().setUp()
        ClosedDay.objects.create(date=date(2026, 11, 6), label='Public holiday')
        AlertRecipient.objects.create(email='boss@example.com')
        self.sign_in(self.night)
        self.thursday_3pm = '2026-11-05T15:00:00+11:00'

    def hours(self, day):
        return [slot.hour for slot in slots_on(day)]

    def test_thursday_has_9_am_and_3_pm_instead_of_9_pm(self):
        self.assertEqual(self.hours(date(2026, 11, 5)), [9, 15])
        self.assertEqual(self.hours(date(2026, 11, 4)), [9, 21])  # Wednesday is normal

    def test_sunday_before_a_monday_holiday_has_no_reading_at_all(self):
        ClosedDay.objects.create(date=MONDAY)
        self.assertEqual(self.hours(date(2026, 11, 1)), [21])  # still scheduled...
        self.assertEqual(storage_closure(at(1, 21)), 'Public holiday')  # ...but not due

    def test_the_3_pm_reading_can_be_saved_and_so_can_the_usual_9_pm_one(self):
        self.assertEqual(self.storage(self.coolroom, '3.0', slot=self.thursday_3pm).status_code, 201)
        late = self.storage(self.freezer, '-18.0', slot='2026-11-05T21:00:00+11:00')
        self.assertEqual(late.status_code, 201)  # logged anyway
        self.assertEqual(self.storage(self.coolroom, '3.0', slot='2026-11-05T16:00:00+11:00').status_code, 400)

    def test_reminders_and_missed_follow_the_3_pm_reading(self):
        self.assertEqual([a.kind for a in send_due_alerts(at(5, 14, 30))], ['reminder'])
        self.assertEqual([a.kind for a in send_due_alerts(at(5, 18))], ['reminder2'])
        self.assertEqual(send_due_alerts(at(5, 20, 30)), [])  # nothing for 9 pm
        thursday = [m['slot'].hour for m in missed_storage_slots(at(5, 22)) if m['slot'].day == 5]
        self.assertIn(15, thursday)
        self.assertNotIn(21, thursday)

    def test_the_report_shows_the_3_pm_reading_in_the_9_pm_row(self):
        self.storage(self.coolroom, '3.0', slot=self.thursday_3pm)
        self.storage(self.freezer, '-12.0', slot=self.thursday_3pm, corrective={'action': 'discarded', 'notes': 'Done'})
        sheet = storage_sheets(date(2026, 11, 2), date(2026, 11, 6))[0]
        names = sheet['units']
        thursday_9pm = [r for r in sheet['rows'] if r['kind'] == 'time' and r['label'] == '9.00 PM'][4]  # Sun, Mon, Tue, Wed, Thu
        self.assertEqual(thursday_9pm['cells'][0][names.index('Coolroom')], '3.0 (3pm)')
        self.assertEqual(thursday_9pm['cells'][0][names.index('Freezer')], '-12.0 (3pm)*')
        self.assertIsNone(thursday_9pm['closed'][0])  # not "Public holiday": the reading is due at 3 pm

    def test_two_holidays_in_a_row_only_the_last_one_keeps_its_9_pm(self):
        # Mon 2 and Tue 3 Nov are holidays; Wednesday is a working day.
        ClosedDay.objects.create(date=date(2026, 11, 2))
        ClosedDay.objects.create(date=date(2026, 11, 3))
        self.assertEqual(storage_closure(at(1, 21)), 'Public holiday')  # Sunday: off
        self.assertEqual(storage_closure(at(2, 9)), 'Public holiday')
        self.assertEqual(storage_closure(at(2, 15)), 'Public holiday')  # Monday's moved 3 pm: Monday is closed itself
        self.assertEqual(storage_closure(at(3, 9)), 'Public holiday')
        self.assertIsNone(storage_closure(at(3, 21)))  # Tuesday 9 pm: the next day is a working day
        self.assertIsNone(storage_closure(at(4, 9)))
