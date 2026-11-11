from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    action_label = serializers.CharField(source='get_action_display', read_only=True)
    user_name = serializers.CharField(source='user.display_name', read_only=True)
    staff_name = serializers.CharField(source='staff.name', read_only=True, default='')

    class Meta:
        model = AuditLog
        fields = ['id', 'at', 'action', 'action_label', 'user_name', 'staff_name', 'summary', 'reason']
