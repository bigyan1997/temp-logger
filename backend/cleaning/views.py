from datetime import date, timedelta

from django.db import transaction
from django.db.models import Max
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from accounts.permissions import IsAdminRole
from alerts.models import AlertSent
from audit.models import AuditLog, record
from reports.grids import MAX_DAYS
from setup.views import ConfigViewSet

from .day import day_status
from .models import CleaningCheck, CleaningTask
from .pdf import render_cleaning
from .reminders import due_tasks
from .serializers import CleaningCheckSerializer, CleaningTaskSerializer, SaveDaySerializer

DEFAULT_PDF_DAYS = 35  # five weeks, one sheet of the paper table


class CleaningTaskViewSet(ConfigViewSet):
    """The tasks (columns of Table 8). Managed on the Cleaning module's Tasks page."""

    queryset = CleaningTask.objects.all()
    serializer_class = CleaningTaskSerializer


class CleaningPagination(PageNumberPagination):
    page_size = 100


class CleaningCheckViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Day staff only. A tick is saved once and never edited or deleted: a mistake is voided with a reason."""

    permission_classes = [IsAdminRole]
    serializer_class = CleaningCheckSerializer
    pagination_class = CleaningPagination

    def get_queryset(self):
        checks = CleaningCheck.objects.select_related('task', 'recorded_by', 'entered_by')
        # Only the list hides voided ones, so a voided one can still be opened.
        if self.action == 'list' and self.request.query_params.get('include_voided') != '1':
            checks = checks.filter(voided=False)
        params = self.request.query_params
        if params.get('from'):
            checks = checks.filter(date__gte=params['from'])
        if params.get('to'):
            checks = checks.filter(date__lte=params['to'])
        if params.get('task'):
            checks = checks.filter(task_id=params['task'])
        return checks

    def create(self, request):
        """Save the tasks ticked on a day. A task already ticked that day is left as it is, unless it can be done
        more than once a day (stock put away): then each tick is another time it was done."""
        serializer = SaveDaySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        day, person = serializer.validated_data['date'], serializer.validated_data['recorded_by']
        with transaction.atomic():
            for tick in serializer.validated_data['ticks']:
                task = tick['task']
                earlier = CleaningCheck.objects.filter(task=task, date=day, voided=False)
                if earlier.exists() and not task.repeatable:
                    continue
                number = (earlier.aggregate(Max('number'))['number__max'] or 0) + 1
                CleaningCheck.objects.create(
                    task=task, date=day, number=number, note=tick['note'], recorded_by=person, entered_by=request.user,
                )
        return Response(day_status(day), status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def day(self, request):
        """What is due and already ticked on ?date= (default today)."""
        try:
            day = date.fromisoformat(request.query_params.get('date', timezone.localdate().isoformat()))
        except ValueError:
            return Response({'date': 'Use a date like 2026-11-02.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(day_status(day))

    @action(detail=False, methods=['get'])
    def notifications(self, request):
        """Monthly and quarterly tasks that are due now, and the reminder emails already sent about them."""
        due = [
            {
                'task': item['task'].pk,
                'name': item['task'].name,
                'frequency_label': item['task'].get_frequency_display(),
                'state': item['state'],
                'due_date': item['due_date'],
                'days_late': item['days_late'],
                'last_done': item['last_done'],
            }
            for item in due_tasks(timezone.localdate())
        ]
        names = dict(CleaningTask.objects.values_list('pk', 'name'))
        sent = [
            {
                'id': alert.id,
                'sent_at': alert.sent_at,
                'name': names.get(int(alert.key.split(':')[0]), ''),
                'what': 'Task due' if alert.kind == 'cleaning_due' else 'Still not done (reminder)',
            }
            for alert in AlertSent.objects.filter(kind__startswith='cleaning_').order_by('-sent_at')[:50]
        ]
        return Response({'count': len(due), 'due': due, 'sent': sent})

    @action(detail=True, methods=['post'])
    def void(self, request, pk=None):
        check = self.get_object()
        if check.voided:
            return Response({'detail': 'This entry is already voided.'}, status=status.HTTP_400_BAD_REQUEST)
        reason = str(request.data.get('reason', '')).strip()
        if len(reason) < 3:
            return Response({'reason': 'Say why this entry is being voided.'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            check.voided = True
            check.void_reason = reason[:300]
            check.save(update_fields=['voided', 'void_reason'])
            record(request.user, AuditLog.Action.VOIDED, f'Voided: {check}', reason, module=AuditLog.Module.CLEANING)
        return Response(self.get_serializer(check).data)

    @action(detail=False, methods=['get'])
    def pdf(self, request):
        """Table 8 as a PDF. ?from=YYYY-MM-DD&to=YYYY-MM-DD (default: the last five weeks)."""
        today = timezone.localdate()
        try:
            end = date.fromisoformat(request.query_params.get('to', today.isoformat()))
            start = date.fromisoformat(request.query_params.get('from', (end - timedelta(days=DEFAULT_PDF_DAYS - 1)).isoformat()))
        except ValueError:
            return Response({'message': 'Use dates like 2026-11-02.'}, status=status.HTTP_400_BAD_REQUEST)
        if start > end or (end - start).days >= MAX_DAYS:
            return Response({'message': f'Choose a period of up to {MAX_DAYS} days.'}, status=status.HTTP_400_BAD_REQUEST)
        response = HttpResponse(render_cleaning(start, end), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="cleaning-{start}-to-{end}.pdf"'
        return response
