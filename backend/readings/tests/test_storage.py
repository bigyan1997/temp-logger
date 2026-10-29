import uuid

from readings.models import CorrectiveAction, StorageReading

from .base import MONDAY_9AM, MONDAY_9PM, TUESDAY_9AM, ReadingTestCase

FIX = {'action': 'used_immediately', 'hours_above_limit': '1.0'}


class SaveStorageReadingTests(ReadingTestCase):
    def setUp(self):
        super().setUp()
        self.sign_in(self.night)

    def test_saves_an_in_range_reading_with_who_and_what_limit(self):
        response = self.storage(self.coolroom, '2.4')
        self.assertEqual(response.status_code, 201, response.json())

        reading = StorageReading.objects.get()
        self.assertEqual(reading.status, 'ok')
        self.assertEqual(str(reading.limit_at_time), '5.0')
        self.assertEqual(reading.entered_by, self.night)
        self.assertEqual(reading.recorded_by, self.sam)

    def test_out_of_limit_needs_a_corrective_action_and_saves_nothing_without_it(self):
        response = self.storage(self.coolroom, '6.5')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['code'], 'corrective_required')
        self.assertEqual(StorageReading.objects.count(), 0)

    def test_out_of_limit_saves_together_with_its_corrective_action(self):
        response = self.storage(self.coolroom, '6.5', corrective=FIX)
        self.assertEqual(response.status_code, 201, response.json())
        self.assertEqual(response.json()['status'], 'out_of_limit')
        self.assertEqual(response.json()['corrective_action']['action'], 'used_immediately')
        self.assertEqual(CorrectiveAction.objects.count(), 1)

    def test_corrective_action_rejected_when_not_needed(self):
        self.assertEqual(self.storage(self.coolroom, '2.0', corrective=FIX).status_code, 400)

    def test_corrective_action_must_suit_the_kind_of_check(self):
        wrong = {'action': 'rejected'}  # a receiving action
        self.assertEqual(self.storage(self.coolroom, '6.5', corrective=wrong).status_code, 400)

    def test_frozen_reading_above_zero_must_be_confirmed(self):
        response = self.storage(self.freezer, '15.6', corrective=FIX)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['code'], 'needs_confirmation')
        self.assertIn('minus', response.json()['message'])

        confirmed = self.storage(self.freezer, '15.6', corrective=FIX, confirm_unusual=True)
        self.assertEqual(confirmed.status_code, 201, confirmed.json())

    def test_big_jump_from_the_last_reading_must_be_confirmed(self):
        self.storage(self.coolroom, '2.0', slot=MONDAY_9AM)
        response = self.storage(self.coolroom, '3.0', slot=MONDAY_9PM)
        self.assertEqual(response.status_code, 201)

        self.storage(self.freezer, '-18.0', slot=MONDAY_9AM)
        jump = self.storage(self.freezer, '-5.0', slot=MONDAY_9PM, corrective=FIX)
        self.assertEqual(jump.status_code, 422)
        self.assertEqual(jump.json()['code'], 'needs_confirmation')

    def test_impossible_temperature_is_rejected(self):
        self.assertEqual(self.storage(self.coolroom, '99').status_code, 400)

    def test_same_unit_and_time_cannot_be_logged_twice(self):
        self.assertEqual(self.storage(self.coolroom, '2.0').status_code, 201)
        self.assertEqual(self.storage(self.coolroom, '2.5').status_code, 400)
        self.assertEqual(self.storage(self.coolroom, '2.5', slot=TUESDAY_9AM).status_code, 201)

    def test_time_must_be_a_scheduled_slot(self):
        self.assertEqual(self.storage(self.coolroom, '2.0', slot='2026-11-02T10:00:00+11:00').status_code, 400)

    def test_deactivated_unit_and_person_are_rejected(self):
        self.coolroom.active = False
        self.coolroom.save()
        self.assertEqual(self.storage(self.coolroom, '2.0').status_code, 400)

        self.sam.active = False
        self.sam.save()
        self.assertEqual(self.storage(self.freezer, '-18').status_code, 400)

    def test_the_person_is_required(self):
        response = self.client.post(
            '/api/storage-readings/',
            {'unit': self.coolroom.pk, 'slot': MONDAY_9AM, 'value': '2.0'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('recorded_by', response.json())

    def test_resending_the_same_entry_saves_only_once(self):
        entry_id = str(uuid.uuid4())
        first = self.storage(self.coolroom, '2.0', id=entry_id)
        again = self.storage(self.coolroom, '2.0', id=entry_id)
        self.assertEqual((first.status_code, again.status_code), (201, 200))
        self.assertEqual(StorageReading.objects.count(), 1)

    def test_the_readings_text_uses_sydney_time(self):
        self.storage(self.coolroom, '2.0', slot=MONDAY_9PM)
        self.assertTrue(str(StorageReading.objects.get()).endswith('at 02/11 21:00'))

    def test_old_readings_keep_the_limit_they_were_judged_against(self):
        self.storage(self.coolroom, '4.5')
        self.coolroom.max_temp = 3
        self.coolroom.save()
        self.assertEqual(str(StorageReading.objects.get().limit_at_time), '5.0')

    def test_login_is_required(self):
        self.client.logout()
        self.assertIn(self.storage(self.coolroom, '2.0').status_code, (401, 403))


class ListStorageReadingTests(ReadingTestCase):
    def setUp(self):
        super().setUp()
        self.sign_in(self.night)
        self.storage(self.coolroom, '2.0', slot=MONDAY_9AM)
        self.storage(self.freezer, '-18.0', slot=MONDAY_9AM)
        self.storage(self.coolroom, '6.5', slot=MONDAY_9PM, corrective=FIX)

    def values(self, url):
        return sorted(r['value'] for r in self.client.get(url).json()['results'])

    def test_night_sees_their_own_recent_entries(self):
        self.assertEqual(len(self.values('/api/storage-readings/')), 3)

        other_night = type(self.night).objects.create_user('n2@x.com', email='n2@x.com', password='pw-12345-xyz')
        self.sign_in(other_night)
        self.assertEqual(self.values('/api/storage-readings/'), [])

    def test_admin_can_filter(self):
        self.sign_in(self.admin)
        self.assertEqual(len(self.values('/api/storage-readings/')), 3)
        self.assertEqual(self.values(f'/api/storage-readings/?unit={self.freezer.pk}'), ['-18.0'])
        self.assertEqual(self.values('/api/storage-readings/?status=out_of_limit'), ['6.5'])
        self.assertEqual(len(self.values('/api/storage-readings/?from=2026-11-03')), 0)
        self.assertEqual(len(self.values('/api/storage-readings/?from=2026-11-02&to=2026-11-02')), 3)
