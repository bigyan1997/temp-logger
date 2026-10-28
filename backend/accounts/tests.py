from django.test import TestCase
from rest_framework.test import APIClient

from .models import User


class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.night = User.objects.create_user('sam@example.com', email='sam@example.com', password='correct-horse-42', role='night')
        self.admin = User.objects.create_user('dana@example.com', email='dana@example.com', password='correct-horse-42', role='admin')

    def test_login_success_returns_user(self):
        r = self.client.post('/api/auth/login/', {'email': 'sam@example.com', 'password': 'correct-horse-42'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['role'], 'night')

    def test_login_email_is_case_insensitive(self):
        r = self.client.post('/api/auth/login/', {'email': 'SAM@Example.com', 'password': 'correct-horse-42'})
        self.assertEqual(r.status_code, 200)

    def test_login_wrong_password(self):
        r = self.client.post('/api/auth/login/', {'email': 'sam@example.com', 'password': 'nope'})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['code'], 'invalid_credentials')

    def test_me_requires_login(self):
        self.assertIn(self.client.get('/api/auth/me/').status_code, (401, 403))

    def test_me_after_login_then_logout(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/api/auth/me/').json()['email'], 'dana@example.com')
        self.assertEqual(self.client.post('/api/auth/logout/').status_code, 204)
        self.assertIn(self.client.get('/api/auth/me/').status_code, (401, 403))

    def test_inactive_user_cannot_log_in(self):
        self.night.is_active = False
        self.night.save()
        r = self.client.post('/api/auth/login/', {'email': 'sam@example.com', 'password': 'correct-horse-42'})
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


class LoginManagementTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            'dana@example.com', email='dana@example.com', password='correct-horse-42', role='admin'
        )
        self.night = User.objects.create_user(
            'sam@example.com', email='sam@example.com', password='correct-horse-42', role='night'
        )

    def test_night_cannot_manage_logins(self):
        self.client.force_login(self.night)
        self.assertEqual(self.client.get('/api/users/').status_code, 403)

    def test_admin_creates_a_login_that_can_sign_in(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            '/api/users/',
            {'email': 'New@Example.com', 'first_name': 'New', 'role': 'night', 'password': 'a-long-pass-77'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertNotIn('password', response.json())

        self.client.logout()
        sign_in = self.client.post('/api/auth/login/', {'email': 'new@example.com', 'password': 'a-long-pass-77'})
        self.assertEqual(sign_in.status_code, 200)

    def test_new_login_needs_a_password(self):
        self.client.force_login(self.admin)
        response = self.client.post('/api/users/', {'email': 'x@example.com', 'role': 'night'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_admin_resets_a_password(self):
        self.client.force_login(self.admin)
        response = self.client.patch(f'/api/users/{self.night.pk}/', {'password': 'brand-new-pass-5'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.night.refresh_from_db()
        self.assertTrue(self.night.check_password('brand-new-pass-5'))

    def test_admin_cannot_deactivate_or_demote_themselves(self):
        self.client.force_login(self.admin)
        url = f'/api/users/{self.admin.pk}/'
        self.assertEqual(self.client.patch(url, {'is_active': False}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(url, {'role': 'night'}, format='json').status_code, 400)

    def test_email_cannot_be_changed(self):
        self.client.force_login(self.admin)
        response = self.client.patch(f'/api/users/{self.night.pk}/', {'email': 'other@example.com'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_no_delete(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.delete(f'/api/users/{self.night.pk}/').status_code, 405)
