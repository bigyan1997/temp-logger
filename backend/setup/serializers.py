from rest_framework import serializers

from .models import Run, StaffMember, Supplier, Unit


def tidy(text):
    """Trim and collapse repeated spaces."""
    return ' '.join(text.split())


class UniqueNameMixin:
    """Tidies one text field and rejects duplicates, ignoring capital letters.

    Set `unique_field` on the serializer (default: "name")."""

    unique_field = 'name'
    unique_message = 'That is already on the list.'

    def validate(self, attrs):
        if self.unique_field not in attrs:
            return attrs

        value = tidy(attrs[self.unique_field])
        if not value:
            raise serializers.ValidationError({self.unique_field: 'This cannot be empty.'})
        attrs[self.unique_field] = value

        same = self.Meta.model.objects.filter(**{f'{self.unique_field}__iexact': value})
        if self.instance:
            same = same.exclude(pk=self.instance.pk)
        if same.exists():
            raise serializers.ValidationError({self.unique_field: self.unique_message})
        return attrs


class StaffMemberSerializer(UniqueNameMixin, serializers.ModelSerializer):
    unique_message = 'That name is already on the list.'

    class Meta:
        model = StaffMember
        fields = ['id', 'name', 'active']


class UnitSerializer(UniqueNameMixin, serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ['id', 'name', 'kind', 'max_temp', 'active']

    def validate_max_temp(self, value):
        if not -40 <= value <= 30:
            raise serializers.ValidationError('Enter a limit between -40 and 30 °C.')
        return value


class SupplierSerializer(UniqueNameMixin, serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['id', 'name', 'active']


class RunSerializer(UniqueNameMixin, serializers.ModelSerializer):
    unique_field = 'code'

    class Meta:
        model = Run
        fields = ['id', 'code', 'active']

    def validate_code(self, value):
        return value.strip().upper()


class RecordedBySerializerMixin:
    """For reading serializers: only people currently on the list can be picked."""

    def validate_recorded_by(self, value):
        if not value.active:
            raise serializers.ValidationError('Pick a name from the list.')
        return value
