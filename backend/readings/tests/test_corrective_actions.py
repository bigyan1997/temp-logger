from audit.models import AuditLog
from readings.models import CorrectiveAction
from setup.models import StaffMember

from .base import ReadingTestCase


class CorrectiveActionTests(ReadingTestCase):
    def setUp(self):
        super().setUp()
        self.jess = StaffMember.objects.create(name='Jess', can_sign_off=True)  # a manager
        self.sign_in(self.night)
        self.dispatch('5.4', corrective={'action': 'rechecked'})  # taken by Sam, who is not a manager
        self.action = CorrectiveAction.objects.get()

    def sign_off(self, staff=None, **extra):
        return self.client.post(
            f'/api/corrective-actions/{self.action.pk}/signoff/', {'staff': (staff or self.jess).pk, **extra}, format='json'
        )

    def test_night_sees_only_what_is_waiting(self):
        waiting = self.client.get('/api/corrective-actions/').json()['results']
        self.assertEqual([a['id'] for a in waiting], [self.action.pk])
        self.assertEqual(waiting[0]['logged_by_name'], 'Sam')

        self.sign_off()
        self.assertEqual(self.client.get('/api/corrective-actions/').json()['results'], [])  # signed ones are admin-only

    def test_night_manager_can_sign_off(self):
        signed = self.sign_off()
        self.assertEqual(signed.status_code, 200)
        self.assertEqual(signed.json()['signed_off_by_name'], 'Jess')
        entry = AuditLog.objects.get(action='signed_off')
        self.assertTrue(entry.summary.endswith('signed off by Jess'))
        self.assertEqual(entry.user, self.night)  # the login is recorded as well as the person

    def test_admin_sees_it_waiting_then_signs_it_off(self):
        self.sign_in(self.admin)
        waiting = self.client.get('/api/corrective-actions/?unsigned=1').json()['results']
        self.assertEqual(len(waiting), 1)
        self.assertEqual(waiting[0]['kind'], 'dispatch')
        self.assertIn('5.4', waiting[0]['summary'])

        self.assertEqual(self.sign_off().status_code, 200)
        self.assertEqual(self.client.get('/api/corrective-actions/?unsigned=1').json()['results'], [])
        self.assertEqual(len(self.client.get('/api/corrective-actions/').json()['results']), 1)

    def test_only_a_manager_on_the_list_can_sign_off(self):
        self.assertEqual(self.sign_off(self.sam).status_code, 400)  # Sam is not a manager
        gone = StaffMember.objects.create(name='Gone', can_sign_off=True, active=False)
        self.assertEqual(self.sign_off(gone).status_code, 400)
        self.assertEqual(self.client.post(f'/api/corrective-actions/{self.action.pk}/signoff/', {}, format='json').status_code, 400)
        self.assertIsNone(CorrectiveAction.objects.get().signed_off_at)

    def test_signing_off_your_own_entry_needs_a_note(self):
        self.sam.can_sign_off = True
        self.sam.save()
        self.assertEqual(self.sign_off(self.sam).status_code, 400)
        self.assertEqual(self.sign_off(self.sam, note='   ').status_code, 400)

        signed = self.sign_off(self.sam, note='Only manager on shift; rechecked twice.')
        self.assertEqual(signed.status_code, 200)
        self.assertEqual(signed.json()['signed_off_note'], 'Only manager on shift; rechecked twice.')
        self.assertEqual(AuditLog.objects.get(action='signed_off').reason, 'Only manager on shift; rechecked twice.')

    def test_signing_off_twice_keeps_the_first_sign_off(self):
        first = self.sign_off().json()
        self.sign_in(self.admin)  # the night login no longer sees it once signed
        second = self.sign_off(StaffMember.objects.create(name='Alex', can_sign_off=True)).json()
        self.assertEqual(first['signed_off_at'], second['signed_off_at'])
        self.assertEqual(second['signed_off_by_name'], 'Jess')


class ReadingOptionsTests(ReadingTestCase):
    def test_options_describe_limits_actions_and_slots(self):
        self.sign_in(self.night)
        options = self.client.get('/api/reading-options/').json()
        self.assertEqual(options['limits']['chilled_max'], '5.0')
        self.assertEqual(options['limits']['frozen_max'], '-15.0')
        self.assertIn('rejected', [a['value'] for a in options['corrective_actions']['receiving']])
        self.assertEqual(options['storage_slots']['6'], ['21:00'])
