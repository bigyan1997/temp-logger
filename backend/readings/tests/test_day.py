from datetime import date, datetime
from zoneinfo import ZoneInfo

from readings.day import build_day
from setup.models import Unit

from .base import MONDAY_9AM, ReadingTestCase

SYDNEY = ZoneInfo('Australia/Sydney')
MONDAY = date(2026, 11, 2)


def sydney(day, hour):
    return datetime(2026, 11, day, hour, 0, tzinfo=SYDNEY)


class DayTests(ReadingTestCase):
    def states(self, now):
        return [slot['state'] for slot in build_day(MONDAY, now)['storage']]

    def test_slot_states_through_the_day(self):
        self.assertEqual(self.states(sydney(2, 8)), ['upcoming', 'upcoming'])
        self.assertEqual(self.states(sydney(2, 10)), ['due', 'upcoming'])
        self.assertEqual(self.states(sydney(2, 12)), ['missed', 'upcoming'])
        self.assertEqual(self.states(sydney(2, 23)), ['missed', 'missed'])

    def test_a_day_without_readings_has_no_storage_slots(self):
        self.assertEqual(build_day(date(2026, 11, 7))['storage'], [])  # Saturday

    def test_logged_readings_show_up_and_finish_the_slot(self):
        self.sign_in(self.night)
        self.storage(self.coolroom, '2.0', slot=MONDAY_9AM)
        self.storage(self.freezer, '-18.0', slot=MONDAY_9AM)

        morning = build_day(MONDAY, sydney(2, 12))['storage'][0]
        done = {u['name']: u['reading'] is not None for u in morning['units']}
        self.assertEqual(done, {'Coolroom': True, 'Old Coolroom': False, 'Freezer': True, 'Chest Freezer': False})
        self.assertEqual(morning['state'], 'missed')

        self.storage(Unit.objects.get(name='Old Coolroom'), '2.0', slot=MONDAY_9AM)
        self.storage(Unit.objects.get(name='Chest Freezer'), '-18.0', slot=MONDAY_9AM)
        self.assertEqual(build_day(MONDAY, sydney(2, 12))['storage'][0]['state'], 'done')


class DayApiTests(ReadingTestCase):
    def test_api_returns_the_day(self):
        self.sign_in(self.night)
        self.receiving('4.0')
        self.dispatch('3.0')
        data = self.client.get('/api/day/?date=2026-11-02').json()
        self.assertEqual(data['date'], '2026-11-02')
        self.assertEqual(len(data['storage']), 2)
        posh = [s for s in data['receiving'] if s['name'] == 'Posh Foods'][0]
        self.assertEqual(posh['entry']['temp'], '4.0')
        run_a = [r for r in data['dispatch'] if r['code'] == 'A'][0]
        self.assertEqual(run_a['entry']['temp'], '3.0')
        self.assertIsNone([r for r in data['dispatch'] if r['code'] == 'B'][0]['entry'])

    def test_default_is_today_and_bad_dates_are_rejected(self):
        self.sign_in(self.night)
        self.assertEqual(self.client.get('/api/day/').status_code, 200)
        self.assertEqual(self.client.get('/api/day/?date=nope').status_code, 400)

    def test_login_required(self):
        self.assertIn(self.client.get('/api/day/').status_code, (401, 403))
