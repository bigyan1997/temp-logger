from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase
from django.utils import timezone

from accounts.models import User
from alerts.sender import send_due_alerts
from audit.models import AuditLog
from readings.tests.base import ReadingTestCase
from setup.models import AlertRecipient, ClosedDay

from . import rules
from .models import CleaningCheck, CleaningTask
from .reminders import due_tasks

MONDAY = '2026-11-02'
SYDNEY = ZoneInfo('Australia/Sydney')


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


class ReminderTests(ReadingTestCase):
    def setUp(self):
        super().setUp()
        self.forklift = CleaningTask.objects.get(name__startswith='Forklift')
        self.pest = CleaningTask.objects.get(name__startswith='Pest spray')
        self.bait = CleaningTask.objects.get(name__startswith='Bait change')

    def due(self, day):
        return {item['task'].name.split()[0]: item for item in due_tasks(day)}

    def done_before(self, *tasks):
        """Tick the tasks in an earlier period: reminders only start once a task has been done in the app."""
        admin = User.objects.create_user('old@x.com', email='old@x.com', password='x', role='admin')
        for task in tasks:
            CleaningCheck.objects.create(task=task, date=date(2026, 1, 5), recorded_by=self.sam, entered_by=admin)

    def test_forklift_pest_and_bait_send_reminders_to_start_with(self):
        notified = set(CleaningTask.objects.filter(notify=True).values_list('pk', flat=True))
        self.assertEqual(notified, {self.forklift.pk, self.pest.pk, self.bait.pk})

    def test_a_task_is_due_from_the_first_working_day_of_its_period(self):
        # 1 Nov 2026 is a Sunday, so the forklift is due on Monday 2 November. The quarter began on Thursday 1 October.
        self.assertNotIn('Forklift', self.due(date(2026, 11, 1)))
        self.assertEqual(self.due(date(2026, 11, 2))['Forklift']['due_date'], date(2026, 11, 2))
        self.assertEqual(self.due(date(2026, 11, 2))['Pest']['due_date'], date(2026, 10, 1))

    def test_a_public_holiday_moves_the_due_date(self):
        ClosedDay.objects.create(date=date(2026, 11, 2), label='Holiday')
        self.assertNotIn('Forklift', self.due(date(2026, 11, 2)))
        self.assertEqual(self.due(date(2026, 11, 3))['Forklift']['due_date'], date(2026, 11, 3))

    def test_it_is_overdue_after_a_week_and_stops_when_done_in_that_period(self):
        self.assertEqual(self.due(date(2026, 11, 8))['Forklift']['state'], 'due')
        self.assertEqual(self.due(date(2026, 11, 9))['Forklift']['state'], 'overdue')
        admin = User.objects.create_user('b@x.com', email='b@x.com', password='x', role='admin')
        CleaningCheck.objects.create(task=self.forklift, date=date(2026, 11, 4), recorded_by=self.sam, entered_by=admin)
        self.assertNotIn('Forklift', self.due(date(2026, 11, 9)))
        self.assertEqual(self.due(date(2026, 12, 1))['Forklift']['due_date'], date(2026, 12, 1))  # next month

    def test_emails_go_once_when_due_then_once_a_week_while_not_done(self):
        AlertRecipient.objects.create(email='boss@example.com')
        self.done_before(self.forklift)

        def sent_on(day):
            moment = datetime(day.year, day.month, day.day, 9, 0, tzinfo=SYDNEY)
            return [a.subject for a in send_due_alerts(moment) if a.kind.startswith('cleaning') and 'Forklift' in a.subject]

        self.assertEqual(sent_on(date(2026, 11, 2)), ['Due: Forklift recharge & water (1st of month)'])
        self.assertEqual(sent_on(date(2026, 11, 3)), [])  # nothing new the next day
        week_later = sent_on(date(2026, 11, 9))
        self.assertEqual(len(week_later), 1)
        self.assertTrue(week_later[0].startswith('OVERDUE'))

    def test_no_email_for_a_task_that_has_never_been_ticked(self):
        AlertRecipient.objects.create(email='boss@example.com')
        moment = datetime(2026, 11, 2, 9, 0, tzinfo=SYDNEY)
        self.assertEqual([a for a in send_due_alerts(moment) if a.kind.startswith('cleaning')], [])
        self.assertIn('Forklift', self.due(date(2026, 11, 2)))  # but the app still shows it as due

    def test_the_notifications_page_lists_what_is_due_and_what_was_sent(self):
        AlertRecipient.objects.create(email='boss@example.com')
        self.done_before(self.forklift, self.pest, self.bait)
        self.sign_in(User.objects.create_user('c@x.com', email='c@x.com', password='x', role='admin'))
        send_due_alerts(timezone.now())
        data = self.client.get('/api/cleaning-checks/notifications/').json()
        self.assertEqual(data['count'], len(data['due']))
        self.assertEqual(len(data['sent']), data['count'])
        self.sign_in(self.night)
        self.assertEqual(self.client.get('/api/cleaning-checks/notifications/').status_code, 403)


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
        self.assertEqual(task['times'][0]['done_by'], 'Sam')
        self.assertEqual(task['times'][0]['note'], 'Soap refilled')
        self.assertEqual(CleaningCheck.objects.get().entered_by, self.admin)

    def test_saving_twice_does_not_double_tick(self):
        self.tick(self.bathroom)
        self.assertEqual(self.tick(self.bathroom).status_code, 201)
        self.assertEqual(CleaningCheck.objects.count(), 1)

    def test_a_repeatable_task_can_be_done_again_the_same_day_and_a_normal_one_cannot(self):
        put_away = CleaningTask.objects.get(name='Stock put away')
        self.assertTrue(put_away.repeatable)  # stock comes in several times a day
        self.tick(put_away, self.bathroom)
        self.tick(put_away, self.bathroom)
        self.assertEqual(CleaningCheck.objects.filter(task=put_away).count(), 2)
        self.assertEqual(CleaningCheck.objects.filter(task=self.bathroom).count(), 1)
        tasks = self.client.get(f'/api/cleaning-checks/day/?date={MONDAY}').json()['tasks']
        times = next(t for t in tasks if t['id'] == put_away.pk)['times']
        self.assertEqual([t['number'] for t in times], [1, 2])

    def test_voiding_one_of_several_keeps_the_others_and_the_pdf_shows_how_many(self):
        put_away = CleaningTask.objects.get(name='Stock put away')
        for _ in range(3):
            self.tick(put_away)
        second = CleaningCheck.objects.get(task=put_away, number=2)
        self.client.post(f'/api/cleaning-checks/{second.pk}/void/', {'reason': 'Duplicate'}, format='json')
        self.assertEqual(CleaningCheck.objects.filter(task=put_away, voided=False).count(), 2)
        self.tick(put_away)  # numbering carries on after the highest one still live
        self.assertEqual(sorted(CleaningCheck.objects.filter(task=put_away, voided=False).values_list('number', flat=True)), [1, 3, 4])
        self.assertEqual(self.client.get('/api/cleaning-checks/pdf/?from=2026-11-02&to=2026-11-06').status_code, 200)

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
