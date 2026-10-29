from django.db import connection, transaction

from audit.models import AuditLog
from readings.models import CorrectiveAction, DispatchReading, StorageReading

from .base import ReadingTestCase

FIX = {'action': 'discarded'}


class VoidStorageTests(ReadingTestCase):
    def setUp(self):
        super().setUp()
        self.sign_in(self.night)
        self.created = self.storage(self.freezer, '-12.0', corrective=FIX).json()  # out of limit
        self.url = f"/api/storage-readings/{self.created['id']}/void/"

    def void(self, **body):
        return self.client.post(self.url, body, format='json')

    def test_night_cannot_void(self):
        self.assertEqual(self.void(reason='typo').status_code, 403)

    def test_a_reason_is_required(self):
        self.sign_in(self.admin)
        self.assertEqual(self.void(reason=' ').status_code, 400)
        self.assertFalse(StorageReading.objects.get().voided)

    def test_void_keeps_the_row_and_logs_it(self):
        self.sign_in(self.admin)
        response = self.void(reason='Entered in the wrong unit')
        self.assertEqual(response.status_code, 200, response.json())

        self.assertTrue(StorageReading.objects.get().voided)
        entry = AuditLog.objects.get()
        self.assertEqual(entry.action, 'voided')
        self.assertEqual(entry.reason, 'Entered in the wrong unit')
        self.assertEqual(entry.user, self.admin)

    def test_voided_entries_leave_lists_and_free_the_slot(self):
        self.sign_in(self.admin)
        self.void(reason='wrong unit')
        self.assertEqual(self.client.get('/api/storage-readings/').json()['count'], 0)
        self.assertEqual(self.client.get('/api/storage-readings/?include_voided=1').json()['count'], 1)
        self.assertEqual(self.storage(self.freezer, '-18.0').status_code, 201)

    def test_corrective_actions_of_voided_readings_are_not_waiting_for_sign_off(self):
        self.sign_in(self.admin)
        self.assertEqual(len(self.client.get('/api/corrective-actions/?unsigned=1').json()['results']), 1)
        self.void(reason='wrong unit')
        self.assertEqual(self.client.get('/api/corrective-actions/?unsigned=1').json()['results'], [])
        self.assertEqual(self.client.get('/api/dashboard/').json()['tiles']['awaiting_signoff'], 0)
        self.assertEqual(CorrectiveAction.objects.count(), 1)  # kept for the record

    def test_correction_replaces_the_value_and_links_back(self):
        self.sign_in(self.admin)
        response = self.void(reason='Misread the display', replacement={'value': '-18.0'})
        self.assertEqual(response.status_code, 200, response.json())

        original, corrected = StorageReading.objects.order_by('recorded_at')
        self.assertTrue(original.voided)
        self.assertFalse(corrected.voided)
        self.assertEqual(corrected.supersedes, original)
        self.assertEqual(str(corrected.value), '-18.0')
        self.assertEqual(corrected.status, 'ok')
        self.assertEqual((corrected.unit, corrected.slot), (original.unit, original.slot))
        self.assertEqual(corrected.recorded_by, self.sam)   # still the person who took the reading
        self.assertEqual(corrected.entered_by, self.admin)  # but the admin login saved the correction

    def test_a_refused_correction_undoes_the_void(self):
        self.sign_in(self.admin)
        # -12 is still out of limit, so a corrective action is required and the correction is refused.
        response = self.void(reason='Retyped', replacement={'value': '-12.0'})
        self.assertEqual(response.status_code, 422)
        self.assertFalse(StorageReading.objects.get().voided)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_voiding_twice_is_not_possible(self):
        self.sign_in(self.admin)
        self.void(reason='wrong unit')
        self.assertEqual(self.void(reason='again').status_code, 404)


class VoidOtherKindsTests(ReadingTestCase):
    def test_dispatch_can_be_corrected_too(self):
        self.sign_in(self.night)
        original = self.dispatch('3.0').json()
        self.sign_in(self.admin)
        response = self.client.post(
            f"/api/dispatch-readings/{original['id']}/void/",
            {'reason': 'Typo', 'replacement': {'temp': '3.8'}},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.json())
        live = DispatchReading.objects.get(voided=False)
        self.assertEqual(str(live.temp), '3.8')
        self.assertEqual(live.run, self.run_a)

    def test_receiving_can_be_voided_without_a_correction(self):
        self.sign_in(self.night)
        original = self.receiving('4.0').json()
        self.sign_in(self.admin)
        response = self.client.post(
            f"/api/receiving-checks/{original['id']}/void/",
            {'reason': 'Logged against wrong supplier'},
            format='json',
        )
        self.assertIsNone(response.json()['replacement'])


class AuditTrailTests(ReadingTestCase):
    def test_changing_a_limit_is_logged(self):
        self.sign_in(self.admin)
        self.client.patch(f'/api/units/{self.coolroom.pk}/', {'max_temp': '4'}, format='json')
        entry = AuditLog.objects.get()
        self.assertEqual(entry.action, 'limit_changed')
        self.assertIn('5.0 °C to 4.0 °C', entry.summary)

    def test_editing_other_fields_is_not_logged(self):
        self.sign_in(self.admin)
        self.client.patch(f'/api/units/{self.coolroom.pk}/', {'name': 'Main Coolroom'}, format='json')
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_login_changes_are_logged(self):
        self.sign_in(self.admin)
        self.client.post(
            '/api/users/', {'email': 'new@x.com', 'role': 'night', 'password': 'a-long-pass-77'}, format='json'
        )
        new_id = [u['id'] for u in self.client.get('/api/users/').json() if u['email'] == 'new@x.com'][0]
        self.client.patch(
            f'/api/users/{new_id}/', {'is_active': False, 'password': 'another-pass-88'}, format='json'
        )
        entries = list(AuditLog.objects.order_by('id'))
        self.assertEqual(entries[0].action, 'login_created')
        self.assertIn('deactivated', entries[1].summary)
        self.assertIn('password reset', entries[1].summary)

    def test_only_admin_reads_the_audit_log(self):
        self.sign_in(self.night)
        self.assertEqual(self.client.get('/api/audit-log/').status_code, 403)
        self.sign_in(self.admin)
        self.assertEqual(self.client.get('/api/audit-log/').status_code, 200)

    def test_database_refuses_to_delete_or_change_records(self):
        if connection.vendor != 'postgresql':
            self.skipTest('Database triggers only exist on Postgres')

        self.sign_in(self.night)
        self.storage(self.coolroom, '2.0')
        self.sign_in(self.admin)
        self.client.patch(f'/api/units/{self.coolroom.pk}/', {'max_temp': '4'}, format='json')

        forbidden = [
            'DELETE FROM readings_storagereading',
            'DELETE FROM audit_auditlog',
            "UPDATE audit_auditlog SET reason = 'changed'",
        ]
        for sql in forbidden:
            with self.assertRaises(Exception, msg=sql), transaction.atomic(), connection.cursor() as cursor:
                cursor.execute(sql)
