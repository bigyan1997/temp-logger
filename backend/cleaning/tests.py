from datetime import date

from django.test import SimpleTestCase

from audit.models import AuditLog
from readings.tests.base import ReadingTestCase

from . import rules
from .models import CleaningCheck, CleaningTask

MONDAY = '2026-11-02'


class RuleTests(SimpleTestCase):
    def test_periods_start_on_the_first_of_the_month_or_quarter(self):
        self.assertEqual(rules.period_start('monthly', date(2026, 11, 18)), date(2026, 11, 1))
        self.assertEqual(rules.period_start('quarterly', date(2026, 11, 18)), date(2026, 10, 1))
        self.assertEqual(rules.period_start('quarterly', date(2026, 3, 31)), date(2026, 1, 1))
        self.assertEqual(rules.period_start('daily', date(2026, 11, 18)), date(2026, 11, 18))

    def test_daily_is_due_on_working_days_and_the_rest_until_done(self):
        self.assertTrue(rules.is_due('daily', date(2026, 11, 2), False))
        self.assertFalse(rules.is_due('daily', date(2026, 11, 7), False))  # a Saturday
        self.assertTrue(rules.is_due('monthly', date(2026, 11, 7), False))
        self.assertFalse(rules.is_due('monthly', date(2026, 11, 7), True))


class CleaningApiTests(ReadingTestCase):
    def setUp(self):
        super().setUp()
        self.sign_in(self.admin)
        self.bathroom = CleaningTask.objects.get(name__startswith='Bathroom')
        self.pest = CleaningTask.objects.get(name__startswith='Pest spray')

    def tick(self, *tasks, date=MONDAY, **extra):
        return self.post('/api/cleaning-checks/', date=date, ticks=[{'task': task.pk} for task in tasks], **extra)

    def test_the_paper_tasks_are_there_to_start_with(self):
        self.assertEqual(CleaningTask.objects.filter(active=True).count(), 13)

    def test_night_login_cannot_use_it(self):
        self.sign_in(self.night)
        self.assertEqual(self.tick(self.bathroom).status_code, 403)
        self.assertEqual(self.client.get('/api/cleaning-checks/day/').status_code, 403)

    def test_ticking_saves_who_did_it_and_shows_on_the_day(self):
        response = self.post(
            '/api/cleaning-checks/', date=MONDAY, ticks=[{'task': self.bathroom.pk, 'note': 'Soap refilled'}])
        self.assertEqual(response.status_code, 201)
        task = next(t for t in response.json()['tasks'] if t['id'] == self.bathroom.pk)
        self.assertTrue(task['done'])
        self.assertEqual(task['done_by'], 'Sam')
        self.assertEqual(task['note'], 'Soap refilled')
        self.assertEqual(CleaningCheck.objects.get().entered_by, self.admin)

    def test_saving_twice_does_not_double_tick(self):
        self.tick(self.bathroom)
        self.assertEqual(self.tick(self.bathroom).status_code, 201)
        self.assertEqual(CleaningCheck.objects.count(), 1)

    def test_a_name_and_at_least_one_task_are_needed(self):
        self.assertEqual(self.post('/api/cleaning-checks/', date=MONDAY, ticks=[]).status_code, 400)
        self.assertEqual(self.tick(self.bathroom, recorded_by=None).status_code, 400)

    def test_a_deactivated_task_or_a_future_day_is_refused(self):
        self.bathroom.active = False
        self.bathroom.save()
        self.assertEqual(self.tick(self.bathroom).status_code, 400)
        self.assertEqual(self.tick(self.pest, date='2999-01-01').status_code, 400)

    def test_a_quarterly_task_stops_being_due_once_done_that_quarter(self):
        def pest(day):
            tasks = self.client.get(f'/api/cleaning-checks/day/?date={day}').json()['tasks']
            return next(t for t in tasks if t['id'] == self.pest.pk)

        self.assertTrue(pest('2026-11-09')['due'])
        self.tick(self.pest, date='2026-11-02')
        later = pest('2026-11-09')
        self.assertFalse(later['due'])
        self.assertEqual(later['last_done'], '2026-11-02')
        self.assertTrue(pest('2027-01-04')['due'])  # next quarter

    def test_voiding_needs_a_reason_is_audited_in_its_own_log_and_lets_it_be_ticked_again(self):
        self.tick(self.bathroom)
        check = CleaningCheck.objects.get()
        self.assertEqual(self.client.post(f'/api/cleaning-checks/{check.pk}/void/', {}, format='json').status_code, 400)
        self.assertEqual(self.client.post(f'/api/cleaning-checks/{check.pk}/void/', {'reason': 'Wrong day'}, format='json').status_code, 200)
        self.assertEqual(self.client.post(f'/api/cleaning-checks/{check.pk}/void/', {'reason': 'Again'}, format='json').status_code, 400)
        self.assertTrue(AuditLog.objects.filter(module='cleaning', reason='Wrong day').exists())
        self.assertEqual(self.client.get('/api/audit-log/').json()['count'], 0)  # not in the Temperature Logger's log
        self.assertEqual(self.client.get('/api/cleaning-checks/').json()['count'], 0)
        self.assertEqual(self.client.get('/api/cleaning-checks/?include_voided=1').json()['count'], 1)
        self.assertEqual(self.tick(self.bathroom).status_code, 201)
        self.assertEqual(CleaningCheck.objects.filter(voided=False).count(), 1)

    def test_list_filters_by_period_and_task(self):
        self.tick(self.bathroom, self.pest, date='2026-11-02')
        self.tick(self.bathroom, date='2026-11-03')
        count = lambda query: self.client.get(f'/api/cleaning-checks/?{query}').json()['count']
        self.assertEqual(count('from=2026-11-03'), 1)
        self.assertEqual(count(f'task={self.pest.pk}'), 1)

    def test_tasks_are_managed_by_admin_and_only_unused_ones_can_be_deleted(self):
        response = self.client.post('/api/cleaning-tasks/', {'name': 'Van clean #9', 'frequency': 'daily'}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.client.post('/api/cleaning-tasks/', {'name': 'van clean #9', 'frequency': 'daily'}, format='json').status_code, 400)
        self.assertEqual(self.client.delete(f'/api/cleaning-tasks/{response.json()["id"]}/').status_code, 204)
        self.tick(self.bathroom)
        self.assertEqual(self.client.delete(f'/api/cleaning-tasks/{self.bathroom.pk}/').status_code, 409)

    def test_the_pdf_opens_even_for_a_voided_tick(self):
        self.tick(self.bathroom)
        self.client.post(f'/api/cleaning-checks/{CleaningCheck.objects.get().pk}/void/', {'reason': 'Wrong day'}, format='json')
        self.tick(self.bathroom, self.pest)
        response = self.client.get('/api/cleaning-checks/pdf/?from=2026-11-02&to=2026-11-06')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b'%PDF'))
        self.assertEqual(self.client.get('/api/cleaning-checks/pdf/?from=2026-11-06&to=2026-11-02').status_code, 400)

    def test_a_note_can_have_several_lines_and_the_pdf_keeps_them(self):
        self.post('/api/cleaning-checks/', date=MONDAY, ticks=[{'task': self.bathroom.pk, 'note': 'Soap refilled' + chr(10) + 'Towels low'}])
        self.assertEqual(CleaningCheck.objects.get().note, 'Soap refilled' + chr(10) + 'Towels low')
        self.assertEqual(self.client.get('/api/cleaning-checks/pdf/?from=2026-11-02&to=2026-11-06').status_code, 200)

    def test_a_void_reason_can_have_several_lines(self):
        self.tick(self.bathroom)
        check = CleaningCheck.objects.get()
        reason = 'Wrong day' + chr(10) + 'Done on Tuesday'
        self.assertEqual(self.client.post(f'/api/cleaning-checks/{check.pk}/void/', {'reason': reason}, format='json').status_code, 200)
        self.assertEqual(self.client.get('/api/cleaning-checks/pdf/?from=2026-11-02&to=2026-11-06').status_code, 200)
