import uuid
from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole
from audit.models import AuditLog, record
from setup.models import Unit

from . import rules
from .choices import ACTIONS_FOR, ProductType, Status
from .dashboard import build_dashboard
from .day import build_day
from .models import CorrectiveAction, DispatchReading, ReceivingCheck, StorageReading
from .schedule import STORAGE_SLOTS
from .serializers import (
    CorrectiveActionSerializer,
    DispatchReadingSerializer,
    ReceivingCheckSerializer,
    SignOffSerializer,
    StorageReadingSerializer,
)

NIGHT_CAN_SEE_LAST = timedelta(days=2)


class ReadingPagination(PageNumberPagination):
    page_size = 100


class ReadingViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Create and look up readings. There is no edit or delete: an admin voids a mistake and can correct it.

    - Night staff see only what their own login saved in the last two days ("My entries").
    - Admin sees everything and can filter with ?from=, ?to= (dates), ?status=, ?include_voided=1
      and the one field named in `filter_field` (unit, supplier or run).
    """

    pagination_class = ReadingPagination

    date_lookup = None    # e.g. 'date' or 'slot__date', the field ?from= and ?to= filter on
    filter_field = None   # e.g. 'unit', also usable as ?unit=<id>

    def get_permissions(self):
        return [IsAdminRole()] if self.action == 'void' else [IsAuthenticated()]

    def get_queryset(self):
        readings = self.serializer_class.Meta.model.objects.select_related(
            'corrective_action', 'recorded_by', 'entered_by'
        )
        user, params = self.request.user, self.request.query_params

        if not user.is_admin_role:
            return readings.filter(
                entered_by=user, voided=False, recorded_at__gte=timezone.now() - NIGHT_CAN_SEE_LAST
            )

        if params.get('include_voided') != '1':
            readings = readings.filter(voided=False)
        if params.get('from'):
            readings = readings.filter(**{f'{self.date_lookup}__gte': params['from']})
        if params.get('to'):
            readings = readings.filter(**{f'{self.date_lookup}__lte': params['to']})
        if params.get('status'):
            readings = readings.filter(status=params['status'])
        if params.get(self.filter_field):
            readings = readings.filter(**{f'{self.filter_field}_id': params[self.filter_field]})
        return readings

    def create(self, request, *args, **kwargs):
        # A retry of an entry that already saved (same id) just returns what was saved.
        saved = self.already_saved(request)
        if saved:
            return Response(self.get_serializer(saved).data, status=status.HTTP_200_OK)
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def void(self, request, pk=None):
        """Admin: cancel an entry (reason required) and, if `replacement` is sent, save the corrected one.

        The original row stays, marked void, and the correction points back at it.
        Anything the replacement does not say is copied from the original (the same unit and time, supplier
        and day, or run and day, and the same person).
        """
        original = self.get_object()
        reason = str(request.data.get('reason', '')).strip()
        if len(reason) < 3:
            return Response({'reason': 'Say why this entry is being voided.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():  # if the correction is refused, the void is undone too
            original.voided = True
            original.save(update_fields=['voided'])

            corrected = None
            if request.data.get('replacement') is not None:
                serializer = self.get_serializer(data=self.replacement_data(original, request.data['replacement']))
                serializer.is_valid(raise_exception=True)
                corrected = serializer.save(supersedes=original)

            record(
                request.user, AuditLog.Action.VOIDED,
                f'{"Corrected" if corrected else "Voided"}: {original}' + (f' -> {corrected}' if corrected else ''),
                reason,
            )

        return Response({
            'voided': str(original.pk),
            'replacement': self.get_serializer(corrected).data if corrected else None,
        })

    def replacement_data(self, original, changes):
        """The corrected entry's fields: what stays the same as the original, plus the changes."""
        data = {'recorded_by': original.recorded_by_id}
        for name in self.serializer_class.identity_fields:
            field = original._meta.get_field(name)
            value = getattr(original, field.attname)
            data[name] = value if field.is_relation else value.isoformat()
        return {**data, **changes}

    def already_saved(self, request):
        try:
            entry_id = uuid.UUID(str(request.data.get('id')))
        except ValueError:
            return None
        return self.serializer_class.Meta.model.objects.filter(pk=entry_id, entered_by=request.user).first()


class StorageReadingViewSet(ReadingViewSet):
    serializer_class = StorageReadingSerializer
    date_lookup = 'slot__date'
    filter_field = 'unit'


class ReceivingCheckViewSet(ReadingViewSet):
    serializer_class = ReceivingCheckSerializer
    date_lookup = 'date'
    filter_field = 'supplier'


class DispatchReadingViewSet(ReadingViewSet):
    serializer_class = DispatchReadingSerializer
    date_lookup = 'date'
    filter_field = 'run'


class CorrectiveActionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Corrective actions (?unsigned=1 for those still waiting) and sign-off.

    Admin sees them all. The night login sees only those waiting, so the night manager can sign off.
    """

    serializer_class = CorrectiveActionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ReadingPagination

    def get_queryset(self):
        actions = CorrectiveAction.objects.live().select_related(
            'storage_reading__unit', 'receiving_check__supplier', 'dispatch_reading__run',
            'storage_reading__recorded_by', 'receiving_check__recorded_by', 'dispatch_reading__recorded_by',
            'signed_off_by', 'signed_off_person',
        )
        waiting_only = self.request.query_params.get('unsigned') == '1' or not self.request.user.is_admin_role
        return actions.filter(signed_off_at__isnull=True) if waiting_only else actions

    @action(detail=True, methods=['post'])
    def signoff(self, request, pk=None):
        """Approve an action. The body names the manager: {"staff": id, "note": "..."} (the logins are shared).

        The note is required when the manager also took the reading.
        """
        corrective_action = self.get_object()
        if corrective_action.signed_off_at is None:
            who = SignOffSerializer(data=request.data, context={'action': corrective_action})
            who.is_valid(raise_exception=True)
            person, note = who.validated_data['staff'], who.validated_data['note'].strip()
            corrective_action.signed_off_by = request.user
            corrective_action.signed_off_person = person
            corrective_action.signed_off_note = note
            corrective_action.signed_off_at = timezone.now()
            corrective_action.save(
                update_fields=['signed_off_by', 'signed_off_person', 'signed_off_note', 'signed_off_at']
            )
            summary = f'{corrective_action.reading} signed off by {person.name}'
            record(request.user, AuditLog.Action.SIGNED_OFF, summary, reason=note)
        return Response(self.get_serializer(corrective_action).data)


class ReadingOptionsView(APIView):
    """Everything the entry screens need to know that is not in the database lists."""

    def get(self, request):
        return Response({
            'limits': {
                'chilled_max': str(rules.CHILLED_MAX),
                'frozen_max': str(rules.FROZEN_MAX),
                'near_margin': str(rules.NEAR_MARGIN),
            },
            'statuses': [{'value': value, 'label': label} for value, label in Status.choices],
            'product_types': [{'value': value, 'label': label} for value, label in ProductType.choices],
            'corrective_actions': {
                kind.value: [{'value': a.value, 'label': a.label} for a in actions]
                for kind, actions in ACTIONS_FOR.items()
            },
            'storage_slots': {
                str(weekday): [t.strftime('%H:%M') for t in times] for weekday, times in STORAGE_SLOTS.items()
            },
        })


class DashboardView(APIView):
    """Admin dashboard: tile counts, missed readings and recent out-of-limit readings."""

    permission_classes = [IsAdminRole]

    def get(self, request):
        return Response(build_dashboard())


class DayView(APIView):
    """What is due and what is already logged on one day (?date=YYYY-MM-DD, default today)."""

    def get(self, request):
        try:
            day = date.fromisoformat(request.query_params['date']) if 'date' in request.query_params else None
        except ValueError:
            return Response({'code': 'bad_date', 'message': 'Use a date like 2026-11-02.'}, status=400)
        return Response(build_day(day or timezone.localdate()))


class TrendsView(APIView):
    """Admin: one unit's storage temperatures over time, for the trend chart.

    ?unit=<id> (required), ?from= and ?to= (dates, default the last 14 days).
    """

    permission_classes = [IsAdminRole]
    DEFAULT_DAYS = 14

    def get(self, request):
        unit = Unit.objects.filter(pk=request.query_params.get('unit')).first()
        if unit is None:
            return Response({'code': 'unit_needed', 'message': 'Choose a unit.'}, status=400)
        try:
            end = date.fromisoformat(request.query_params.get('to', timezone.localdate().isoformat()))
            start = date.fromisoformat(
                request.query_params.get('from', (end - timedelta(days=self.DEFAULT_DAYS - 1)).isoformat())
            )
        except ValueError:
            return Response({'code': 'bad_date', 'message': 'Use dates like 2026-11-02.'}, status=400)

        readings = StorageReading.objects.filter(
            unit=unit, slot__date__gte=start, slot__date__lte=end, voided=False
        ).order_by('slot')
        return Response({
            'unit': {'id': unit.pk, 'name': unit.name, 'limit': str(unit.max_temp)},
            'points': [
                {'slot': r.slot, 'value': str(r.value), 'status': r.status, 'limit': str(r.limit_at_time)}
                for r in readings
            ],
        })
