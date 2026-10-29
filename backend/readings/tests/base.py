from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from setup.models import Run, StaffMember, Supplier, Unit

PASSWORD = 'pw-12345-xyz'

# Scheduled storage times in November 2026 (Sydney is UTC+11 then).
MONDAY_9AM = '2026-11-02T09:00:00+11:00'
MONDAY_9PM = '2026-11-02T21:00:00+11:00'
TUESDAY_9AM = '2026-11-03T09:00:00+11:00'


class ReadingTestCase(TestCase):
    """An API client, an admin and a night login, a staff member, and the seeded lists."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user('a@x.com', email='a@x.com', password=PASSWORD, role='admin')
        self.night = User.objects.create_user('n@x.com', email='n@x.com', password=PASSWORD, role='night')
        self.sam = StaffMember.objects.create(name='Sam')

        self.coolroom = Unit.objects.get(name='Coolroom')
        self.freezer = Unit.objects.get(name='Freezer')
        self.supplier = Supplier.objects.get(name='Posh Foods')
        self.run_a = Run.objects.get(code='A')

    def sign_in(self, user):
        self.client.force_login(user)

    def post(self, url, **fields):
        fields.setdefault('recorded_by', self.sam.pk)
        return self.client.post(url, fields, format='json')

    def storage(self, unit, value, slot=MONDAY_9AM, **extra):
        return self.post('/api/storage-readings/', unit=unit.pk, slot=slot, value=value, **extra)

    def receiving(self, temp=None, date='2026-11-02', **extra):
        return self.post('/api/receiving-checks/', supplier=self.supplier.pk, date=date, temp=temp, **extra)

    def dispatch(self, temp, run=None, date='2026-11-02', **extra):
        return self.post('/api/dispatch-readings/', run=(run or self.run_a).pk, date=date, temp=temp, **extra)
