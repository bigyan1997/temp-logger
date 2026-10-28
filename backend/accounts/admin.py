from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class AccountUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name', 'role', 'is_active')
    list_filter = ('role', 'is_active')
    fieldsets = UserAdmin.fieldsets + (('Temperature Logger', {'fields': ('role',)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Temperature Logger', {'fields': ('first_name', 'last_name', 'role')}),
    )

    # Records are never deleted; deactivate the account instead.
    def has_delete_permission(self, request, obj=None):
        return False
