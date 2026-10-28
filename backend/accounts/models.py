from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """A named staff account. `role` decides what the person can do."""

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin (day)'
        NIGHT = 'night', 'Night'

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.NIGHT)

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    def __str__(self):
        return self.display_name
