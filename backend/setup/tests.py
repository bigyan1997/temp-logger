from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User

from .models import Run, StaffMember, Supplier, Unit

PASSWORD = 'pw-12345-xyz'


class ApiTestCase(TestCase):
    """Gives each test an API client plus an admin and a night login."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user('a@x.com', email='a@x.com', password=PASSWORD, role='admin')
        self.night = User.objects.create_user('n@x.com', email='n@x.com', password=PASSWORD, role='night')


class StaffApiTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.sam = StaffMember.objects.create(name='Sam')
        StaffMember.objects.create(name='Former Person', active=False)

    def names(self, url='/api/staff/'):
        return sorted(s['name'] for s in self.client.get(url).json())

    def test_login_required(self):
        self.assertIn(self.client.get('/api/staff/').status_code, (401, 403))

    def test_night_sees_only_active_names(self):
        self.client.force_login(self.night)
        self.assertEqual(self.names(), ['Sam'])

    def test_night_cannot_ask_for_inactive(self):
        self.client.force_login(self.night)
        self.assertEqual(self.names('/api/staff/?all=1'), ['Sam'])

    def test_admin_can_list_all(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.names('/api/staff/?all=1'), ['Former Person', 'Sam'])

    def test_night_cannot_add(self):
        self.client.force_login(self.night)
        self.assertEqual(self.client.post('/api/staff/', {'name': 'Kim'}).status_code, 403)

    def test_admin_adds_and_deactivates(self):
        self.client.force_login(self.admin)
        created = self.client.post('/api/staff/', {'name': '  Kim   Lee '})
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()['name'], 'Kim Lee')

        off = self.client.patch(f"/api/staff/{created.json()['id']}/", {'active': False}, format='json')
        self.assertEqual(off.status_code, 200)
        self.assertFalse(off.json()['active'])

    def test_duplicate_name_rejected_ignoring_case(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post('/api/staff/', {'name': 'sam'}).status_code, 400)


class ConfigListTests(ApiTestCase):
    def test_defaults_are_seeded(self):
        self.client.force_login(self.night)

        units = {u['name']: u for u in self.client.get('/api/units/').json()}
        self.assertEqual(set(units), {'Coolroom', 'Old Coolroom', 'Freezer', 'Chest Freezer'})
        self.assertEqual(units['Freezer']['max_temp'], '-15.0')

        runs = [r['code'] for r in self.client.get('/api/runs/').json()]
        self.assertEqual(runs, ['A', 'B', 'C', 'D', 'E', 'G', 'H', 'J', 'K', 'L', 'M'])

        self.assertEqual(len(self.client.get('/api/suppliers/').json()), 8)

    def test_night_cannot_change_a_limit(self):
        self.client.force_login(self.night)
        unit = Unit.objects.get(name='Coolroom')
        response = self.client.patch(f'/api/units/{unit.pk}/', {'max_temp': '8'}, format='json')
        self.assertEqual(response.status_code, 403)

    def test_admin_changes_a_limit_within_range_only(self):
        self.client.force_login(self.admin)
        url = f"/api/units/{Unit.objects.get(name='Coolroom').pk}/"
        self.assertEqual(self.client.patch(url, {'max_temp': '4'}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(url, {'max_temp': '99'}, format='json').status_code, 400)

    def test_run_code_is_uppercased_and_unique(self):
        self.client.force_login(self.admin)
        first = self.client.post('/api/runs/', {'code': 'n'}, format='json')
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()['code'], 'N')
        self.assertEqual(self.client.post('/api/runs/', {'code': 'n'}, format='json').status_code, 400)

    def test_nothing_can_be_deleted(self):
        self.client.force_login(self.admin)
        for path, model in [('units', Unit), ('suppliers', Supplier), ('runs', Run)]:
            response = self.client.delete(f'/api/{path}/{model.objects.first().pk}/')
            self.assertEqual(response.status_code, 405, path)

    def test_deactivated_supplier_is_hidden_from_night(self):
        Supplier.objects.filter(name='Posh Foods').update(active=False)
        self.client.force_login(self.night)
        names = [s['name'] for s in self.client.get('/api/suppliers/').json()]
        self.assertNotIn('Posh Foods', names)
