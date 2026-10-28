from django.contrib import admin

from .models import Run, StaffMember, Supplier, Unit


class NoDeleteAdmin(admin.ModelAdmin):
    """Records are never deleted; deactivate them instead."""

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StaffMember, Supplier, Run)
class SimpleListAdmin(NoDeleteAdmin):
    list_filter = ('active',)


@admin.register(Unit)
class UnitAdmin(NoDeleteAdmin):
    list_display = ('name', 'kind', 'max_temp', 'active')
    list_filter = ('kind', 'active')
