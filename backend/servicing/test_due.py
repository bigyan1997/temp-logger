from datetime import date

from alerts.service_check import service_alerts
from readings.tests.base import ReadingTestCase

from .due import equipment_due
from .models import ServiceRecord


class ServiceDueTests(ReadingTestCase):
    def service(self, equipment, day, kind='service'):
        return ServiceRecord.objects.create(
            kind=kind, equipment=equipment, service_date=day, serviced_by='Cool Care', work_done='Checked.',
            recorded_by=self.sam, entered_by=self.admin,
        )

    def test_due_is_six_months_after_the_latest_service_of_each_equipment(self):
        self.service('Coolroom', date(2026, 1, 10))
        self.service('coolroom ', date(2026, 5, 31))  # same equipment, newer
        self.service('Freezer', date(2026, 8, 31))
        due = {item['equipment'].lower(): item for item in equipment_due(date(2026, 11, 25))}
        self.assertEqual(due['coolroom']['due'], date(2026, 11, 30))
        self.assertEqual(due['coolroom']['state'], 'due_soon')
        self.assertEqual(due['freezer']['due'], date(2027, 2, 28))
        self.assertEqual(due['freezer']['state'], 'ok')

    def test_one_record_can_cover_several_pieces_of_equipment(self):
        self.service('Coolroom, Old Coolroom, Freezer', date(2026, 11, 2))
        due = {item['equipment']: item['due'] for item in equipment_due(date(2026, 11, 25))}
        self.assertEqual(due, {n: date(2027, 5, 2) for n in ['Coolroom', 'Old Coolroom', 'Freezer']})

    def test_a_repair_does_not_move_the_due_date(self):
        self.service('Coolroom', date(2026, 5, 31))
        self.service('Coolroom', date(2026, 11, 20), kind='repair')
        (item,) = equipment_due(date(2026, 11, 25))
        self.assertEqual(item['due'], date(2026, 11, 30))

    def test_records_can_be_filtered_by_type(self):
        self.service('Coolroom', date(2026, 5, 31))
        self.service('Coolroom', date(2026, 11, 20), kind='repair')
        self.sign_in(self.admin)
        count = lambda query: self.client.get('/api/service-records/' + query).json()['count']
        self.assertEqual((count(''), count('?kind=repair'), count('?kind=service')), (2, 1, 1))

    def test_emails_once_when_due_soon_and_again_if_overdue(self):
        self.service('Coolroom', date(2026, 5, 31))
        from django.utils import timezone
        soon = timezone.make_aware(timezone.datetime(2026, 11, 25, 9, 0))
        late = timezone.make_aware(timezone.datetime(2026, 12, 5, 9, 0))
        self.assertEqual([a.kind for a in service_alerts(soon)], ['service_due'])
        self.assertEqual([a.kind for a in service_alerts(late)], ['service_overdue'])

    def test_no_emails_when_nothing_is_near(self):
        self.service('Coolroom', date(2026, 11, 2))
        from django.utils import timezone
        self.assertEqual(service_alerts(timezone.make_aware(timezone.datetime(2026, 11, 25, 9, 0))), [])

    def test_due_list_is_for_day_staff(self):
        self.service('Coolroom', date(2026, 5, 31))
        self.sign_in(self.admin)
        self.assertEqual(self.client.get('/api/service-records/due/').status_code, 200)
        self.sign_in(self.night)
        self.assertEqual(self.client.get('/api/service-records/due/').status_code, 403)
