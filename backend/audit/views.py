from rest_framework import mixins, viewsets
from rest_framework.pagination import PageNumberPagination

from accounts.permissions import IsAdminRole

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditPagination(PageNumberPagination):
    page_size = 50


class AuditLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Admin can read the audit log. Nobody can change it."""

    queryset = AuditLog.objects.select_related('user')
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminRole]
    pagination_class = AuditPagination
