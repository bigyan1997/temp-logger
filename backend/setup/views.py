from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsAdminRole
from audit.models import AuditLog, record

from .models import AlertRecipient, Run, StaffMember, Supplier, Unit
from .serializers import (
    AlertRecipientSerializer, RunSerializer, StaffMemberSerializer, SupplierSerializer, UnitSerializer,
)


class ConfigViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """An admin-managed list: staff names, units, suppliers or runs.

    - Anyone signed in can read the active items (the entry forms need them).
    - Only admin can add, edit or deactivate items. Admin can add ?all=1 to
      the list to also see deactivated items.
    - There is no delete: records are never removed.
    """

    pagination_class = None

    def get_permissions(self):
        if self.action == 'list':
            return [IsAuthenticated()]
        return [IsAdminRole()]

    def get_queryset(self):
        items = self.queryset.all()
        user = self.request.user
        is_admin = user.is_authenticated and user.is_admin_role
        sees_everything = self.action != 'list' or self.request.query_params.get('all') == '1'
        if is_admin and sees_everything:
            return items
        return items.filter(active=True)


class StaffMemberViewSet(ConfigViewSet):
    queryset = StaffMember.objects.all()
    serializer_class = StaffMemberSerializer


class UnitViewSet(ConfigViewSet):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer

    def perform_update(self, serializer):
        old_limit = serializer.instance.max_temp
        unit = serializer.save()
        if unit.max_temp != old_limit:
            record(
                self.request.user, AuditLog.Action.LIMIT_CHANGED,
                f'{unit.name} limit changed from {old_limit} °C to {unit.max_temp} °C',
            )


class SupplierViewSet(ConfigViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer


class RunViewSet(ConfigViewSet):
    queryset = Run.objects.all()
    serializer_class = RunSerializer


class AlertRecipientViewSet(ConfigViewSet):
    """Who gets the alert emails. Unlike the other lists, only admin may even read it."""

    queryset = AlertRecipient.objects.all()
    serializer_class = AlertRecipientSerializer

    def get_permissions(self):
        return [IsAdminRole()]
