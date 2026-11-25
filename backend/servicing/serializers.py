from django.utils import timezone
from rest_framework import serializers

from setup.serializers import RecordedBySerializerMixin, tidy

from .drive import copy_status
from .models import ServiceFile, ServiceRecord


class ServiceFileSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    is_picture = serializers.SerializerMethodField()
    copy_status = serializers.SerializerMethodField()
    recorded_by_name = serializers.CharField(source='recorded_by.name', read_only=True)

    class Meta:
        model = ServiceFile
        fields = ['id', 'url', 'original_name', 'content_type', 'is_picture', 'size', 'recorded_by_name', 'recorded_at',
                  'copy_status', 'copy_error']

    def get_is_picture(self, file):
        return file.content_type.startswith('image/')

    def get_copy_status(self, file):
        return copy_status(file)

    def get_url(self, file):
        return f'/api/service-records/files/{file.pk}/'


class ServiceRecordSerializer(RecordedBySerializerMixin, serializers.ModelSerializer):
    number = serializers.CharField(read_only=True)
    kind_label = serializers.CharField(source='get_kind_display', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.name', read_only=True)
    entered_by_name = serializers.CharField(source='entered_by.display_name', read_only=True)
    files = ServiceFileSerializer(many=True, read_only=True)

    class Meta:
        model = ServiceRecord
        fields = ['id', 'number', 'kind', 'kind_label', 'equipment', 'service_date', 'serviced_by', 'work_done', 'invoice_number',
                  'recorded_by', 'recorded_by_name', 'entered_by_name', 'recorded_at', 'files']
        read_only_fields = ['recorded_at']

    def validate_service_date(self, day):
        if day > timezone.localdate():
            raise serializers.ValidationError('The date cannot be in the future.')
        return day

    def validate_equipment(self, value):
        value = tidy(value)
        if not value:
            raise serializers.ValidationError('Say what was serviced.')
        return value

    def validate_serviced_by(self, value):
        value = tidy(value)
        if not value:
            raise serializers.ValidationError('Say who did the service.')
        return value

    def validate_invoice_number(self, value):
        return tidy(value)

    def validate_work_done(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Say what was done.')
        return value


class ServiceEditSerializer(ServiceRecordSerializer):
    """The details that can be corrected afterwards. Who typed the record in (`recorded_by`) never changes."""

    class Meta(ServiceRecordSerializer.Meta):
        fields = ['kind', 'equipment', 'service_date', 'serviced_by', 'work_done', 'invoice_number']
