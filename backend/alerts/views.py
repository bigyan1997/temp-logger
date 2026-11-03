from rest_framework import mixins, viewsets

from accounts.permissions import IsAdminRole

from .models import AlertSent
from .serializers import AlertSentSerializer


class AlertSentViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """The alert emails already sent, newest first. Read-only, admin only."""

    queryset = AlertSent.objects.order_by('-sent_at')
    serializer_class = AlertSentSerializer
    permission_classes = [IsAdminRole]
    pagination_class = None

    def get_queryset(self):
        return super().get_queryset()[:100]
