from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from setup.models import StaffMember
from setup.serializers import RecordedBySerializerMixin, tidy

from .drive import copy_status
from .models import NonConformance, Photo, Update

# What each kind of follow-up must say. A manufacturer being notified, or the report being closed, can be just a
# date and a name.
NEEDS_TEXT = {Update.Kind.RESPONSE, Update.Kind.ACTION, Update.Kind.NOTE}


class UpdateSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source='get_kind_display', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.name', read_only=True)
    entered_by_name = serializers.CharField(source='entered_by.display_name', read_only=True)

    class Meta:
        model = Update
        fields = [
            'id', 'kind', 'kind_label', 'happened_at', 'text', 'recorded_by_name', 'entered_by_name', 'recorded_at',
            'voided', 'void_reason',
        ]


class PhotoSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    copy_status = serializers.SerializerMethodField()
    recorded_by_name = serializers.CharField(source='recorded_by.name', read_only=True)

    class Meta:
        model = Photo
        fields = [
            'id', 'update', 'url', 'original_name', 'size', 'recorded_by_name', 'recorded_at', 'copy_status', 'copy_error',
            'voided', 'void_reason',
        ]

    def get_copy_status(self, photo):
        return copy_status(photo)

    def get_url(self, photo):
        return f'/api/non-conformances/photos/{photo.pk}/'


class NonConformanceSerializer(RecordedBySerializerMixin, serializers.ModelSerializer):
    number = serializers.CharField(read_only=True)
    status = serializers.SerializerMethodField()
    recorded_by_name = serializers.CharField(source='recorded_by.name', read_only=True)
    entered_by_name = serializers.CharField(source='entered_by.display_name', read_only=True)
    updates = UpdateSerializer(many=True, read_only=True)
    photos = PhotoSerializer(many=True, read_only=True)
    # Optional when the report is made: when the manufacturer was told. Saved as the first follow-up.
    notified_at = serializers.DateTimeField(write_only=True, required=False)

    class Meta:
        model = NonConformance
        fields = [
            'id', 'number', 'date', 'product', 'customer', 'manufacturer', 'description', 'recorded_by', 'recorded_by_name',
            'entered_by_name', 'recorded_at', 'notified_at', 'status', 'updates', 'photos', 'voided', 'void_reason',
        ]
        read_only_fields = ['recorded_at', 'voided', 'void_reason']

    def get_status(self, report):
        return 'voided' if report.voided else 'closed' if report.is_closed else 'open'

    def validate_date(self, day):
        if day > timezone.localdate():
            raise serializers.ValidationError('The date cannot be in the future.')
        return day

    def validate_notified_at(self, moment):
        if moment > timezone.now() + timedelta(minutes=5):
            raise serializers.ValidationError('That time is in the future.')
        return moment

    def validate_product(self, value):
        value = tidy(value)
        if not value:
            raise serializers.ValidationError('Say which product it is.')
        return value

    def validate_description(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Describe the problem.')
        return value

    def validate_customer(self, value):
        return tidy(value)

    def validate_manufacturer(self, value):
        return tidy(value)


class AddUpdateSerializer(RecordedBySerializerMixin, serializers.Serializer):
    """A follow-up on a report."""

    kind = serializers.ChoiceField(choices=Update.Kind.choices)
    recorded_by = serializers.PrimaryKeyRelatedField(queryset=StaffMember.objects.all())
    happened_at = serializers.DateTimeField(required=False)
    text = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_happened_at(self, moment):
        if moment > timezone.now() + timedelta(minutes=5):
            raise serializers.ValidationError('That time is in the future.')
        return moment

    def validate(self, attrs):
        attrs['text'] = attrs['text'].strip()
        if attrs['kind'] in NEEDS_TEXT and not attrs['text']:
            raise serializers.ValidationError({'text': 'Write what happened.'})
        return attrs
