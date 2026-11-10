from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from setup.serializers import RecordedBySerializerMixin

from . import rules
from .models import Calibration, GaugeCheck


class GaugeCheckSerializer(serializers.ModelSerializer):
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    difference = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)

    class Meta:
        model = GaugeCheck
        fields = ['unit', 'unit_name', 'gauge_reading', 'probe_reading', 'difference', 'comment']

    def validate_unit(self, unit):
        if not unit.active:
            raise serializers.ValidationError('That unit is not in use.')
        return unit

    # HACCP Table 14: any difference between a gauge and the probe "should be noted". The difference
    # itself is always recorded; the comment is optional, even when it is more than 1 °C (owner, 2026-11-11).


class CalibrationSerializer(RecordedBySerializerMixin, serializers.ModelSerializer):
    """One filled-in Table 14. Whether it passed is worked out here, never trusted from the browser."""

    id = serializers.UUIDField(required=False)
    recorded_by_name = serializers.CharField(source='recorded_by.name', read_only=True)
    entered_by_name = serializers.CharField(source='entered_by.display_name', read_only=True)
    probe_difference = serializers.SerializerMethodField()
    action_label = serializers.CharField(source='get_action_display', read_only=True)
    gauges = GaugeCheckSerializer(many=True, required=False)

    class Meta:
        model = Calibration
        fields = [
            'id', 'date', 'recorded_by', 'recorded_by_name', 'entered_by_name', 'recorded_at',
            'probe_reading', 'probe_difference', 'probe_comment', 'passed', 'action', 'action_label', 'action_notes',
            'gauges', 'voided', 'void_reason',
        ]
        read_only_fields = ['recorded_at', 'passed', 'voided', 'void_reason']

    def get_probe_difference(self, calibration):
        return str(rules.probe_difference(calibration.probe_reading))

    def validate_date(self, day):
        if day > timezone.localdate():
            raise serializers.ValidationError('The date cannot be in the future.')
        return day

    def validate_gauges(self, gauges):
        units = [gauge['unit'] for gauge in gauges]
        if len(units) != len(set(units)):
            raise serializers.ValidationError('Each unit can be checked once.')
        return gauges

    def validate(self, attrs):
        attrs['passed'] = rules.within_margin(rules.probe_difference(attrs['probe_reading']))
        if attrs['passed']:
            attrs['action'], attrs['action_notes'] = '', ''
        elif not attrs.get('action'):
            # The action is required; the note is optional (owner, 2026-11-11).
            raise serializers.ValidationError({'action': 'Say what was done: replaced or repaired.'})
        return attrs

    def create(self, validated_data):
        gauges = validated_data.pop('gauges', [])
        with transaction.atomic():
            calibration = Calibration.objects.create(**validated_data)
            GaugeCheck.objects.bulk_create([GaugeCheck(calibration=calibration, **gauge) for gauge in gauges])
        return calibration
