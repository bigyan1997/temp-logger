from django.core.management.base import BaseCommand

from accounts.models import User

LOGINS = [
    ('admin@achievecafeprovisions.com.au', User.Role.ADMIN, 'Admin'),
    ('night@achievecafeprovisions.com.au', User.Role.NIGHT, 'Night'),
]


class Command(BaseCommand):
    help = (
        'Creates the two shared logins (admin@ and night@) on a new database, for example on the orders PC. '
        'Existing logins are left alone unless --reset-passwords is given.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--password', required=True, help='Password to give the new logins.')
        parser.add_argument('--reset-passwords', action='store_true', help='Also set this password on logins that already exist.')

    def handle(self, *args, password, reset_passwords, **options):
        for email, role, name in LOGINS:
            login, created = User.objects.get_or_create(
                username=email, defaults={'email': email, 'role': role, 'first_name': name}
            )
            if created or reset_passwords:
                login.set_password(password)
            if role == User.Role.ADMIN:
                login.is_staff = login.is_superuser = True  # may open /admin/ as a back-up tool
            login.save()
            self.stdout.write(f'{"Created" if created else "Already existed"}: {email} ({role})')
