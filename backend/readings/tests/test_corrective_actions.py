from audit.models import AuditLog
from readings.models import CorrectiveAction
from setup.models import StaffMember

from .base import ReadingTestCase


class CorrectiveActionTests(ReadingTestCase):
    def setUp(self):
        super().setUp()
        self.sign_in(self.night)
        self.dispatch('5.4', corrective={'action': 'rechecked'})
        self.action = CorrectiveAction.objects.get()

    def sign_off(self, staff=None):
        return self.client.post(
            f'/api/corrective-actions/{self.action.pk}/signoff/', {'staff': (staff or self.sam).pk}, format='json'
        )

    def test_night_cannot_list_or_sign_off(self):
        self.assertEqual(self.client.get('/api/corrective-actions/').status_code, 403)
        self.assertEqual(self.sign_off().status_code, 403)

    def test_admin_sees_it_waiting_then_signs_it_off(self):
        self.sign_in(self.admin)
        waiting = self.client.get('/api/corrective-actions/?unsigned=1').json()['results']
        self.assertEqual(len(waiting), 1)
        self.assertEqual(waiting[0]['kind'], 'dispatch')
        self.assertIn('5.4', waiting[0]['summary'])
        self.assertEqual(waiting[0]['logged_by_name'], 'Sam')

        signed = self.sign_off()
        self.assertEqual(signed.status_code, 200)
        self.assertEqual(signed.json()['signed_off_by_name'], 'Sam')
        self.assertEqual(AuditLog.objects.get(action='signed_off').summary.endswith('signed off by Sam'), True)
        self.assertEqual(self.client.get('/api/corrective-actions/?unsigned=1').json()['results'], [])

    def test_signing_off_twice_keeps_the_first_sign_off(self):
        self.sign_in(self.admin)
        first = self.sign_off().json()
        second = self.sign_off(StaffMember.objects.create(name='Alex')).json()
        self.assertEqual(first['signed_off_at'], second['signed_off_at'])
        self.assertEqual(second['signed_off_by_name'], 'Sam')

    def test_sign_off_needs_a_name_from_the_active_list(self):
        self.sign_in(self.admin)
        url = f'/api/corrective-actions/{self.action.pk}/signoff/'
        self.assertEqual(self.client.post(url, {}, format='json').status_code, 400)
        gone = StaffMember.objects.create(name='Gone', active=False)
        self.assertEqual(self.sign_off(gone).status_code, 400)
        self.assertEqual(CorrectiveAction.objects.get().signed_off_at, None)


class ReadingOptionsTests(ReadingTestCase):
    def test_options_describe_limits_actions_and_slots(self):
        self.sign_in(self.night)
        options = self.client.get('/api/reading-options/').json()
        self.assertEqual(options['limits']['chilled_max'], '5.0')
        self.assertEqual(options['limits']['frozen_max'], '-15.0')
        self.assertIn('rejected', [a['value'] for a in options['corrective_actions']['receiving']])
        self.assertEqual(options['storage_slots']['6'], ['21:00'])
