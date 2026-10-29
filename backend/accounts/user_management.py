"""Admin-only management of logins (who can sign in and with what role)."""

from django.contrib.auth.password_validation import validate_password
from rest_framework import mixins, serializers, viewsets
from rest_framework.routers import DefaultRouter

from audit.models import AuditLog, record

from .models import User
from .permissions import IsAdminRole


class LoginAccountSerializer(serializers.ModelSerializer):
    """One login. The email is also the username, so it is set once at creation."""

    display_name = serializers.CharField(read_only=True)
    password = serializers.CharField(write_only=True, required=False, trim_whitespace=False)

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'display_name', 'role', 'is_active', 'password']

    def validate_email(self, value):
        email = value.strip().lower()
        if self.instance and email != self.instance.email.lower():
            raise serializers.ValidationError('The email cannot be changed. Add a new login instead.')
        if User.objects.filter(email__iexact=email).exclude(pk=getattr(self.instance, 'pk', None)).exists():
            raise serializers.ValidationError('There is already a login with this email.')
        return email

    def validate_password(self, value):
        validate_password(value, self.instance)
        return value

    def validate(self, attrs):
        if self.instance is None and not attrs.get('password'):
            raise serializers.ValidationError({'password': 'Set a password for the new login.'})

        # Stops the admin locking themselves out by accident.
        if self.instance and self.instance == self.context['request'].user:
            if attrs.get('is_active') is False:
                raise serializers.ValidationError({'is_active': 'You cannot deactivate your own login.'})
            if attrs.get('role', self.instance.role) != User.Role.ADMIN:
                raise serializers.ValidationError({'role': 'You cannot remove your own admin role.'})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        return User.objects.create_user(
            username=validated_data['email'], password=password, **validated_data
        )

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save(update_fields=['password'])
        return instance


class LoginAccountViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """List, add and edit logins. There is no delete: deactivate a login instead."""

    queryset = User.objects.order_by('role', 'email')
    serializer_class = LoginAccountSerializer
    permission_classes = [IsAdminRole]
    pagination_class = None

    def perform_create(self, serializer):
        login = serializer.save()
        record(self.request.user, AuditLog.Action.LOGIN_CREATED, f'Login created: {login.email} ({login.role})')

    def perform_update(self, serializer):
        before = {'role': serializer.instance.role, 'active': serializer.instance.is_active}
        password_reset = bool(serializer.validated_data.get('password'))
        login = serializer.save()

        changes = []
        if login.role != before['role']:
            changes.append(f'role is now {login.role}')
        if login.is_active != before['active']:
            changes.append('reactivated' if login.is_active else 'deactivated')
        if password_reset:
            changes.append('password reset')
        if changes:
            record(self.request.user, AuditLog.Action.LOGIN_CHANGED, f'{login.email}: {", ".join(changes)}')


router = DefaultRouter()
router.register('users', LoginAccountViewSet, basename='user')
