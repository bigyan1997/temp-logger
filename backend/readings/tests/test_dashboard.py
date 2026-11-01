from datetime import datetime
from zoneinfo import ZoneInfo

from readings.dashboard import build_dashboard, missed_storage_slots
from setup.models import StaffMember

from .base import MONDAY_9AM, ReadingTestCase

SYDNEY = ZoneInfo('Australia/Sydney')
FIX = {'action': 'discarded'}


def sydney(day, hour, minute=0):
    return datetime(2026, 11, day, hour, minute, tzinfo=SYDNEY)


class MissedSlotTests(ReadingTestCase):
    def missed(self, now):
        return [(m['unit'].name, m['slot']) for m in missed_storage_slots(now)]

    def test_nothing_is_missed_before_the_grace_period_ends(self):
        # Sunday 10:00: Saturday has no readings and Sunday's 9 PM reading is not due yet.
        self.assertEqual(self.missed(sydney(1, 10)), [])
        # Monday 10:30 is only 1.5 hours after the 9 AM reading was due.
        slots = {slot for _, slot in self.missed(sydney(2, 10, 30))}
        self.assertNotIn(sydney(2, 9), slots)

    def test_unlogged_units_are_missed_after_the_grace_period(self):
        missed = self.missed(sydney(2, 11, 30))
        self.assertEqual({unit for unit, _ in missed}, {'Coolroom', 'Old Coolroom', 'Freezer', 'Chest Freezer'})
        # Sunday night's reading was never logged either.
        self.assertEqual({slot for _, slot in missed}, {sydney(1, 21), sydney(2, 9)})

    def test_logged_units_are_not_missed(self):
        self.sign_in(self.night)
        self.storage(self.coolroom, '2.0', slot=MONDAY_9AM)
        monday_morning = {unit for unit, slot in self.missed(sydney(2, 11, 30)) if slot == sydney(2, 9)}
        self.assertNotIn('Coolroom', monday_morning)
        self.assertIn('Freezer', monday_morning)

    def test_deactivated_units_are_ignored(self):
        self.coolroom.active = False
        self.coolroom.save()
        names = {unit for unit, _ in self.missed(sydney(2, 11, 30))}
        self.assertNotIn('Coolroom', names)

    def test_yesterday_counts_too(self):
        # Tuesday 7 AM: Monday's 9 PM slot is long past; Tuesday's 9 AM is not yet due.
        slots = {slot for _, slot in self.missed(sydney(3, 7))}
        self.assertEqual(slots, {sydney(2, 9), sydney(2, 21)})


class DashboardApiTests(ReadingTestCase):
    def test_night_cannot_open_the_dashboard(self):
        self.sign_in(self.night)
        self.assertEqual(self.client.get('/api/dashboard/').status_code, 403)

    def test_tiles_count_attention_items(self):
        self.sign_in(self.night)
        self.storage(self.coolroom, '2.0', slot=MONDAY_9AM)
        self.storage(self.freezer, '-12.0', slot=MONDAY_9AM, corrective=FIX)
        self.dispatch('3.0')

        self.sign_in(self.admin)
        data = self.client.get('/api/dashboard/').json()
        self.assertEqual(data['tiles']['logged_today'], 3)
        self.assertEqual(data['tiles']['out_of_limit'], 1)
        self.assertEqual(data['tiles']['awaiting_signoff'], 1)
        self.assertEqual(data['out_of_limit'][0]['kind'], 'storage')
        self.assertEqual(data['out_of_limit'][0]['recorded_by'], 'Sam')
        self.assertFalse(data['out_of_limit'][0]['signed_off'])

    def test_signing_off_clears_the_awaiting_count(self):
        self.sign_in(self.night)
        self.dispatch('6.0', corrective=FIX)
        self.sign_in(self.admin)
        manager = StaffMember.objects.create(name='Jess', can_sign_off=True)
        action_id = self.client.get('/api/corrective-actions/').json()['results'][0]['id']
        self.client.post(f'/api/corrective-actions/{action_id}/signoff/', {'staff': manager.pk}, format='json')
        tiles = self.client.get('/api/dashboard/').json()['tiles']
        self.assertEqual(tiles['awaiting_signoff'], 0)
