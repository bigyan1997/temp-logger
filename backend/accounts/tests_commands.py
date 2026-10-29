from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from .models import User


class CreateDefaultLoginsTests(TestCase):
    def test_creates_both_logins_that_can_sign_in(self):
        call_command('create_default_logins', password='a-long-pass-77', stdout=StringIO())
        admin = User.objects.get(email='admin@achievecafeprovisions.com.au')
        night = User.objects.get(email='night@achievecafeprovisions.com.au')
        self.assertEqual((admin.role, night.role), ('admin', 'night'))
        self.assertTrue(admin.check_password('a-long-pass-77'))
        self.assertFalse(night.is_staff)

    def test_existing_logins_keep_their_password_unless_reset(self):
        call_command('create_default_logins', password='first-pass-123', stdout=StringIO())
        call_command('create_default_logins', password='second-pass-456', stdout=StringIO())
        self.assertTrue(User.objects.get(role='night').check_password('first-pass-123'))

        call_command('create_default_logins', password='second-pass-456', reset_passwords=True, stdout=StringIO())
        self.assertTrue(User.objects.get(role='night').check_password('second-pass-456'))
