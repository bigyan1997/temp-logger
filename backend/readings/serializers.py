from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import APIException

from setup.models import StaffMember
from setup.serializers import RecordedBySerializerMixin

from . import rules
from .choices import ACTIONS_FOR, Action, CheckKind, ProductType, Status
from .models import CorrectiveAction, DispatchReading, ReceivingCheck, StorageReading
from .schedule import is_storage_slot


class UnprocessableEntry(APIException):
    """The entry is understood but cannot be saved yet. The screen reacts to `code`."""

    status_code = 422

    def __init__(self, code, message, **extra):
        super().__init__({'code': code, 'message': message, **extra})


class CorrectiveActionInputSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=Action.choices)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    hours_above_limit = serializers.DecimalField(
        max_digits=4, decimal_places=1, min_value=0, required=False, allow_null=True
    )


class SignOffSerializer(serializers.Serializer):
    """Who is approving: a person currently on the staff list."""

    staff = serializers.PrimaryKeyRelatedField(
        queryset=StaffMember.objects.filter(active=True), error_messages={'does_not_exist': 'Pick a name from the list.'}
    )


class CorrectiveActionSerializer(serializers.ModelSerializer):
    """A corrective action as shown to the screen, with a one-line summary of its reading."""

    kind = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    action_label = serializers.CharField(source='get_action_display', read_only=True)
    signed_off_by_name = serializers.CharField(source='signed_off_name', default=None, read_only=True)
    logged_by_name = serializers.SerializerMethodField()

    class Meta:
        model = CorrectiveAction
        fields = [
            'id', 'kind', 'summary', 'action', 'action_label', 'notes', 'hours_above_limit',
            'created_at', 'logged_by_name', 'signed_off_at', 'signed_off_by_name',
        ]

    def get_kind(self, action):
        if action.storage_reading_id:
            return CheckKind.STORAGE
        return CheckKind.RECEIVING if action.receiving_check_id else CheckKind.DISPATCH

    def get_summary(self, action):
        return str(action.reading)

    def get_logged_by_name(self, action):
        return action.reading.recorded_by.name


class ReadingSerializer(RecordedBySerializerMixin, serializers.ModelSerializer):
    """Saves one reading and, when it is out of limit, its corrective action, together.

    The flow for every kind of reading:
      1. reject duplicates;
      2. work out the status against the limit;
      3. if the value looks odd, ask the user to confirm it (`confirm_unusual`);
      4. if it is out of limit, require a corrective action (`corrective`).

    Subclasses say which kind of reading they are and how to measure it.
    """

    kind = None             # a CheckKind
    parent_field = None     # the CorrectiveAction field that points at this reading
    identity_fields = ()    # what makes a correction "the same reading" (copied from the original)

    recorded_by_name = serializers.CharField(source='recorded_by.name', read_only=True)
    entered_by_name = serializers.CharField(source='entered_by.display_name', read_only=True)
    confirm_unusual = serializers.BooleanField(write_only=True, default=False)
    corrective = CorrectiveActionInputSerializer(write_only=True, required=False)
    corrective_action = CorrectiveActionSerializer(read_only=True)

    # What subclasses fill in -----------------------------------------------

    def check_not_duplicate(self, attrs):
        raise NotImplementedError

    def measurement(self, attrs):
        """Return (value, limit, previous_value) or None when nothing was measured."""
        raise NotImplementedError

    def has_other_problem(self, attrs):
        """True if something besides temperature needs a corrective action."""
        return False

    # The shared flow --------------------------------------------------------

    def validate(self, attrs):
        self.check_not_duplicate(attrs)

        status, limit = Status.OK, None
        measured = self.measurement(attrs)
        if measured:
            value, limit, previous = measured
            low, high = rules.POSSIBLE_RANGE
            if not low <= value <= high:
                raise serializers.ValidationError({'value': f'Enter a temperature between {low} and {high} °C.'})
            status = rules.status_for(value, limit)

            reasons = rules.unusual_reasons(value, limit, previous)
            if reasons and not attrs['confirm_unusual']:
                raise UnprocessableEntry('needs_confirmation', ' '.join(reasons), warnings=reasons)

        self.check_corrective_action(attrs, needed=status == Status.OUT_OF_LIMIT or self.has_other_problem(attrs))
        attrs['status'] = status
        attrs['limit_at_time'] = limit
        return attrs

    def check_corrective_action(self, attrs, needed):
        corrective = attrs.get('corrective')
        if needed and not corrective:
            raise UnprocessableEntry(
                'corrective_required', 'This needs a corrective action before it can be saved.'
            )
        if corrective and not needed:
            raise serializers.ValidationError({'corrective': 'No corrective action is needed for this entry.'})
        if corrective and corrective['action'] not in ACTIONS_FOR[self.kind]:
            raise serializers.ValidationError({'corrective': 'That action does not apply to this kind of check.'})

    @transaction.atomic
    def create(self, validated_data):
        corrective = validated_data.pop('corrective', None)
        validated_data.pop('confirm_unusual')
        validated_data['entered_by'] = self.context['request'].user
        validated_data['recorded_at'] = timezone.now()

        reading = super().create(validated_data)
        if corrective:
            CorrectiveAction.objects.create(**{self.parent_field: reading}, **corrective)
        return reading


COMMON_FIELDS = [
    'id', 'recorded_by', 'recorded_by_name', 'entered_by_name', 'recorded_at', 'status', 'limit_at_time',
    'note', 'voided', 'supersedes', 'confirm_unusual', 'corrective', 'corrective_action',
]
READ_ONLY_FIELDS = ['recorded_at', 'status', 'limit_at_time', 'voided', 'supersedes']


class StorageReadingSerializer(ReadingSerializer):
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    kind = CheckKind.STORAGE
    parent_field = 'storage_reading'
    identity_fields = ('unit', 'slot')

    class Meta:
        model = StorageReading
        fields = COMMON_FIELDS + ['unit', 'unit_name', 'slot', 'value']
        read_only_fields = READ_ONLY_FIELDS
        validators = []  # duplicates are checked in check_not_duplicate, with a friendlier message

    def validate_unit(self, unit):
        if not unit.active:
            raise serializers.ValidationError('This unit is deactivated.')
        return unit

    def validate_slot(self, slot):
        if not is_storage_slot(slot):
            raise serializers.ValidationError('That is not a scheduled reading time.')
        return slot

    def check_not_duplicate(self, attrs):
        if StorageReading.objects.filter(unit=attrs['unit'], slot=attrs['slot'], voided=False).exists():
            raise serializers.ValidationError('This unit already has a reading for that time.')

    def measurement(self, attrs):
        previous = (
            StorageReading.objects.filter(unit=attrs['unit'], slot__lt=attrs['slot'], voided=False)
            .order_by('-slot')
            .values_list('value', flat=True)
            .first()
        )
        return attrs['value'], attrs['unit'].max_temp, previous


class ReceivingCheckSerializer(ReadingSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    kind = CheckKind.RECEIVING
    parent_field = 'receiving_check'
    identity_fields = ('supplier', 'date')

    class Meta:
        model = ReceivingCheck
        fields = COMMON_FIELDS + ['supplier', 'supplier_name', 'date', 'no_delivery', 'temp', 'product_type', 'packaging_ok']
        read_only_fields = READ_ONLY_FIELDS
        validators = []

    def validate_supplier(self, supplier):
        if not supplier.active:
            raise serializers.ValidationError('This supplier is deactivated.')
        return supplier

    def validate(self, attrs):
        if attrs.get('no_delivery'):
            if attrs.get('temp') is not None:
                raise serializers.ValidationError({'temp': 'Leave the temperature empty when nothing was delivered.'})
        elif attrs.get('temp') is None:
            raise serializers.ValidationError({'temp': 'Enter the temperature of the delivery.'})
        return super().validate(attrs)

    def check_not_duplicate(self, attrs):
        if ReceivingCheck.objects.filter(supplier=attrs['supplier'], date=attrs['date'], voided=False).exists():
            raise serializers.ValidationError('This supplier already has an entry for that day.')

    def measurement(self, attrs):
        if attrs.get('no_delivery'):
            return None
        product_type = attrs.get('product_type', ProductType.CHILLED)
        return attrs['temp'], rules.limit_for_product(product_type), None

    def has_other_problem(self, attrs):
        return not attrs.get('packaging_ok', True)


class DispatchReadingSerializer(ReadingSerializer):
    run_code = serializers.CharField(source='run.code', read_only=True)
    kind = CheckKind.DISPATCH
    parent_field = 'dispatch_reading'
    identity_fields = ('run', 'date')

    class Meta:
        model = DispatchReading
        fields = COMMON_FIELDS + ['run', 'run_code', 'date', 'temp']
        read_only_fields = READ_ONLY_FIELDS
        validators = []

    def validate_run(self, run):
        if not run.active:
            raise serializers.ValidationError('This run is deactivated.')
        return run

    def check_not_duplicate(self, attrs):
        if DispatchReading.objects.filter(run=attrs['run'], date=attrs['date'], voided=False).exists():
            raise serializers.ValidationError('This run already has a reading for that day.')

    def measurement(self, attrs):
        return attrs['temp'], rules.CHILLED_MAX, None
