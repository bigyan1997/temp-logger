import uuid

from django.db import transaction
from django.http import HttpResponse
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from accounts.permissions import IsAdminRole
from audit.models import AuditLog, record

from .models import Calibration
from .pdf import render_calibration
from .saving import file_name, save_copies
from .serializers import CalibrationSerializer
from .status import current_status


class CalibrationPagination(PageNumberPagination):
    page_size = 50


class CalibrationViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Day staff only. A calibration is created once and never edited or deleted: a mistake is voided with a reason
    and the check is done again."""

    permission_classes = [IsAdminRole]
    serializer_class = CalibrationSerializer
    pagination_class = CalibrationPagination

    def get_queryset(self):
        calibrations = Calibration.objects.select_related('recorded_by', 'entered_by').prefetch_related('gauges__unit')
        if self.request.query_params.get('include_voided') != '1':
            calibrations = calibrations.filter(voided=False)
        return calibrations

    def create(self, request, *args, **kwargs):
        # A retry of one that already saved (same id) just returns what was saved.
        try:
            saved = Calibration.objects.filter(pk=uuid.UUID(str(request.data.get('id')))).first()
        except ValueError:
            saved = None
        if saved:
            return Response(self.get_serializer(saved).data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        calibration = serializer.save(entered_by=request.user)
        copies = save_copies(calibration)
        return Response({**self.get_serializer(calibration).data, 'copies': copies}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def void(self, request, pk=None):
        calibration = self.get_object()
        reason = str(request.data.get('reason', '')).strip()
        if len(reason) < 3:
            return Response({'reason': 'Say why this calibration is being voided.'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            calibration.voided = True
            calibration.void_reason = reason[:300]
            calibration.save(update_fields=['voided', 'void_reason'])
            record(request.user, AuditLog.Action.VOIDED, f'Voided: {calibration}', reason, module=AuditLog.Module.CALIBRATION)
        return Response(self.get_serializer(calibration).data)

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        calibration = self.get_object()
        response = HttpResponse(render_calibration(calibration), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{file_name(calibration)}"'
        return response

    @action(detail=False, methods=['get'])
    def due(self, request):
        """When the next 6-monthly calibration is due: state is never, ok, due_soon or overdue."""
        return Response(current_status())
