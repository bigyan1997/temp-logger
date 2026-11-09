from django.utils import timezone

from .models import Calibration
from .rules import due_state


def current_status(today=None):
    """Where the 6-monthly calibration stands today, with the date of the last pass."""
    today = today or timezone.localdate()
    last = Calibration.objects.filter(passed=True, voided=False).order_by('-date').first()
    return {**due_state(last.date if last else None, today), 'last_passed': last.date if last else None}
