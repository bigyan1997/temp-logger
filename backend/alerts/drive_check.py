"""Emails when non-conformance photos have been waiting a long time for their Google Drive copy.

A photo is always kept on this PC, and the 5-minute task keeps retrying the Drive copy, so a short internet drop
sorts itself out. Hours of waiting usually means the Google sign-in has expired or been removed: run
`python manage.py drive_authorize` again (docs/DEPLOYMENT.md, step 11a). Goes to SYSTEM_ALERT_EMAIL, once a day."""

from datetime import timedelta

from django.utils import timezone

from nonconformance.drive import copy_status
from nonconformance.models import Photo

from .checks import Alert

WAIT = timedelta(hours=3)  # long enough for a short internet drop to sort itself out


def stuck_photos(now):
    waiting = Photo.objects.filter(voided=False, recorded_at__lte=now - WAIT).select_related('report')
    return [photo for photo in waiting if copy_status(photo) == 'waiting']


def drive_upload_alerts(now):
    stuck = stuck_photos(now)
    if not stuck:
        return []
    count = len(stuck)
    lead = (
        f'{count} non-conformance photo{"" if count == 1 else "s"} {"has" if count == 1 else "have"} been waiting '
        f'more than {WAIT.seconds // 3600} hours to copy to Google Drive. They are safe on the orders PC.'
    )
    problem = next((photo.copy_error for photo in stuck if photo.copy_error), '')
    body = (
        f'{lead}\nLast problem: {problem or "not known"}\n'
        'If the Google sign-in has expired, run "python manage.py drive_authorize" in the backend folder on the '
        'orders PC (docs/DEPLOYMENT.md, step 11a). The waiting photos then copy by themselves within 5 minutes.'
    )
    items = tuple(f'{photo.report.number}: {photo.original_name}' for photo in stuck[:10])
    day = timezone.localdate(now).isoformat()  # at most one email a day while it lasts
    return [Alert('drive_upload', day, 'GOOGLE DRIVE UPLOAD STUCK', body, lead=lead, items=items, tone='failed')]
