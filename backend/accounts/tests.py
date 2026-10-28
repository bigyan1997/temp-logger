from django.test import TestCase
from rest_framework.test import APIClient

from .models import User


class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.night = User.objects.create_user('sam', password='correct-horse-42', role='night')
        self.admin = User.objects.create_user('dana', password='correct-horse-42', role='admin')

    def test_login_success_returns_user(self):
        r = self.client.post('/api/auth/login/', {'username': 'sam', 'password': 'correct-horse-42'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['role'], 'night')

    def test_login_wrong_password(self):
        r = self.client.post('/api/auth/login/', {'username': 'sam', 'password': 'nope'})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['code'], 'invalid_credentials')

    def test_me_requires_login(self):
        self.assertIn(self.client.get('/api/auth/me/').status_code, (401, 403))

    def test_me_after_login_then_logout(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/api/auth/me/').json()['username'], 'dana')
        self.assertEqual(self.client.post('/api/auth/logout/').status_code, 204)
        self.assertIn(self.client.get('/api/auth/me/').status_code, (401, 403))

    def test_inactive_user_cannot_log_in(self):
        self.night.is_active = False
        self.night.save()
        r = self.client.post('/api/auth/login/', {'username': 'sam', 'password': 'correct-horse-42'})
        self.assertEqual(r.status_code, 400)

    def test_change_password(self):
        self.client.force_login(self.night)
        r = self.client.post(
            '/api/auth/change-password/',
            {'current_password': 'correct-horse-42', 'new_password': 'a-much-longer-pass-9'},
        )
        self.assertEqual(r.status_code, 204)
        self.night.refresh_from_db()
        self.assertTrue(self.night.check_password('a-much-longer-pass-9'))

    def test_change_password_rejects_weak(self):
        self.client.force_login(self.night)
        r = self.client.post(
            '/api/auth/change-password/',
            {'current_password': 'correct-horse-42', 'new_password': '1234'},
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['code'], 'weak_password')

    def test_health_is_public(self):
        self.assertEqual(self.client.get('/api/health/').status_code, 200)


class RolePermissionTests(TestCase):
    def test_is_admin_role_flag(self):
        self.assertTrue(User(role='admin').is_admin_role)
        self.assertFalse(User(role='night').is_admin_role)
