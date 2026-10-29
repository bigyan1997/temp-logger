from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    action_label = serializers.CharField(source='get_action_display', read_only=True)
    user_name = serializers.CharField(source='user.display_name', read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'at', 'action', 'action_label', 'user_name', 'summary', 'reason']
