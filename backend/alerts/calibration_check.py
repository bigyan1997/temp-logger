"""Emails about the 6-monthly thermometer calibration: once when it comes within 15 days, once if it goes overdue.

Nothing is sent while no calibration has ever been recorded (a new install), only the app shows that."""

from django.utils import timezone

from calibration.status import current_status

from .checks import Alert


def calibration_alerts(now):
    status = current_status(timezone.localdate(now))
    due = status['due']
    if status['state'] == 'due_soon':
        when = f'{due:%A %d %B %Y}'
        days = status['days_left']
        lead = (
            f'The 6-monthly thermometer calibration (Table 14) is due on {when}, '
            f'{"today" if days == 0 else f"in {days} day" + ("" if days == 1 else "s")}.'
        )
        return [Alert('calibration', due.isoformat(), f'Thermometer calibration due on {due:%d %B %Y}', lead, lead=lead, tone='reminder')]
    if status['state'] == 'overdue':
        lead = f'The 6-monthly thermometer calibration (Table 14) was due on {due:%A %d %B %Y} and has not been done.'
        return [Alert('calibration_overdue', due.isoformat(), 'THERMOMETER CALIBRATION OVERDUE', lead, lead=lead, tone='failed')]
    return []
