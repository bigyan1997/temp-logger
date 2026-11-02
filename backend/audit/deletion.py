"""Deleting an item from a Settings list (supplier, run, unit, staff name, alert email, login).

Only an item that nothing refers to can go. If readings, checks or audit entries point at it, the database
refuses (those links are protected) and the admin is told to deactivate it instead, so records keep their names.
"""

from django.db import transaction
from django.db.models import ProtectedError
from rest_framework.exceptions import APIException

from .models import AuditLog, record


class InUse(APIException):
    status_code = 409
    default_code = 'in_use'


def delete_unused(user, item, label):
    """Delete `item` if nothing uses it and note it in the audit log. `label` names it, e.g. "supplier: Posh Foods"."""
    try:
        with transaction.atomic():
            item.delete()
    except ProtectedError:
        raise InUse({
            'code': 'in_use',
            'message': f'{label} already has records, so it cannot be deleted. Deactivate it instead.',
        })
    record(user, AuditLog.Action.DELETED, f'Deleted {label}')
