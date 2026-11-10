from django.utils import timezone
from rest_framework import serializers

from setup.models import StaffMember
from setup.serializers import RecordedBySerializerMixin, UniqueNameMixin

from .models import CleaningCheck, CleaningTask


class CleaningTaskSerializer(UniqueNameMixin, serializers.ModelSerializer):
    frequency_label = serializers.CharField(source='get_frequency_display', read_only=True)

    class Meta:
        model = CleaningTask
        fields = ['id', 'name', 'frequency', 'frequency_label', 'active']


class CleaningCheckSerializer(serializers.ModelSerializer):
    task_name = serializers.CharField(source='task.name', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.name', read_only=True)
    entered_by_name = serializers.CharField(source='entered_by.display_name', read_only=True)

    class Meta:
        model = CleaningCheck
        fields = [
            'id', 'task', 'task_name', 'date', 'recorded_by_name', 'entered_by_name', 'recorded_at', 'note',
            'voided', 'void_reason',
        ]


class TickSerializer(serializers.Serializer):
    task = serializers.PrimaryKeyRelatedField(queryset=CleaningTask.objects.all())
    note = serializers.CharField(max_length=300, required=False, allow_blank=True, default='')

    def validate_task(self, task):
        if not task.active:
            raise serializers.ValidationError('That task is not in use.')
        return task


class SaveDaySerializer(RecordedBySerializerMixin, serializers.Serializer):
    """The tasks ticked on one day, saved together."""

    date = serializers.DateField()
    recorded_by = serializers.PrimaryKeyRelatedField(queryset=StaffMember.objects.all())
    ticks = TickSerializer(many=True, allow_empty=False)

    def validate_date(self, day):
        if day > timezone.localdate():
            raise serializers.ValidationError('The date cannot be in the future.')
        return day
