from django.contrib import admin

from .models import CorrectiveAction, DispatchReading, ReceivingCheck, StorageReading


class ReadOnlyAdmin(admin.ModelAdmin):
    """Readings are records: view them here, but never add, change or delete them."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StorageReading, ReceivingCheck, DispatchReading, CorrectiveAction)
class RecordAdmin(ReadOnlyAdmin):
    pass
