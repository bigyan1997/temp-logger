from rest_framework import serializers

from .models import AlertSent

KIND_LABELS = {
    'reminder': 'Reminder: readings due',
    'reminder2': 'Still not logged',
    'out_of_limit': 'Out-of-limit reading',
    'cleaning_due': 'Cleaning task due',
    'cleaning_late': 'Cleaning task overdue',
}


class AlertSentSerializer(serializers.ModelSerializer):
    what = serializers.SerializerMethodField()
    # Reminder keys are the reading time (an ISO date-time), so it can be shown; other keys are internal ids.
    reading_time = serializers.SerializerMethodField()

    class Meta:
        model = AlertSent
        fields = ['id', 'sent_at', 'what', 'reading_time']

    def get_what(self, obj):
        return KIND_LABELS.get(obj.kind, obj.kind)

    def get_reading_time(self, obj):
        return obj.key if obj.kind in ('reminder', 'reminder2') else None
