from readings.models import CorrectiveAction

from .base import ReadingTestCase


class CorrectiveActionNoteTests(ReadingTestCase):
    """What was done about an out-of-limit reading must be written down, or the reading cannot be saved."""

    def setUp(self):
        super().setUp()
        self.sign_in(self.night)

    def test_a_note_is_required(self):
        for corrective in ({'action': 'rechecked'}, {'action': 'rechecked', 'notes': ''}, {'action': 'rechecked', 'notes': '   '}):
            response = self.dispatch('5.4', corrective=corrective)
            self.assertEqual(response.status_code, 400, corrective)
            self.assertIn('Add a note', str(response.json()))
        self.assertEqual(CorrectiveAction.objects.count(), 0)

    def test_it_saves_with_a_note_and_shows_it_with_the_reading(self):
        response = self.dispatch('5.4', corrective={'action': 'rechecked', 'notes': 'Rechecked, now 4.2'})
        self.assertEqual(response.status_code, 201, response.json())
        self.assertEqual(response.json()['corrective_action']['notes'], 'Rechecked, now 4.2')
        self.assertEqual(CorrectiveAction.objects.get().notes, 'Rechecked, now 4.2')

    def test_the_note_is_needed_for_every_kind_of_reading(self):
        needs_note = {'action': 'rejected'}
        self.assertEqual(self.receiving('13.0', corrective=needs_note).status_code, 400)
        self.assertEqual(self.storage(self.freezer, '-12.0', corrective={'action': 'used_immediately'}).status_code, 400)

    def test_there_is_no_sign_off_any_more(self):
        self.dispatch('5.4', corrective={'action': 'rechecked', 'notes': 'Done'})
        action = CorrectiveAction.objects.get()
        self.assertEqual(self.client.get('/api/corrective-actions/').status_code, 404)
        self.assertEqual(self.client.post(f'/api/corrective-actions/{action.pk}/signoff/', {}, format='json').status_code, 404)


class ReadingOptionsTests(ReadingTestCase):
    def test_options_describe_limits_actions_and_slots(self):
        self.sign_in(self.night)
        options = self.client.get('/api/reading-options/').json()
        self.assertEqual(options['limits']['chilled_max'], '5.0')
        self.assertEqual(options['limits']['frozen_max'], '-15.0')
        self.assertIn('rejected', [a['value'] for a in options['corrective_actions']['receiving']])
        self.assertEqual(options['storage_slots']['6'], ['21:00'])
