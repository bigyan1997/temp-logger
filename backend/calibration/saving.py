"""Saves a copy of a finished calibration's PDF: always in the project's report_exports folder, plus the
Google Drive folder or synced folder from settings (the same places the 4-week reports go)."""

from django.conf import settings
from django.utils import timezone

from reports.destinations import LocalFolder, extra_destinations

from .pdf import render_calibration

SUBFOLDER = 'calibration'


def file_name(calibration):
    # The time is in the name so a second calibration on the same day (after a void) never overwrites the first.
    return f'{calibration.date:%Y-%m-%d} {timezone.localtime(calibration.recorded_at):%H%M} - Thermometer calibration.pdf'


def save_copies(calibration):
    """Render the PDF and save it. Never raises: a Drive problem must not lose the calibration itself.

    Returns {'saved': [where, ...], 'problems': [text, ...]}."""
    saved, problems = [], []
    try:
        pdf = render_calibration(calibration)
    except Exception as error:  # the calibration is already saved; the PDF can be downloaded again later
        return {'saved': [], 'problems': [f'The PDF could not be made: {error}']}

    name = file_name(calibration)
    try:
        places = [LocalFolder(settings.REPORTS_LOCAL_DIR / SUBFOLDER, create=True)]
    except Exception as error:
        places = []
        problems.append(f'The copy on this computer could not be saved: {error}')
    try:
        places += extra_destinations()
    except Exception as error:
        problems.append(f'Google Drive could not be reached: {error}')

    for place in places:
        try:
            place.save(name, pdf)
            saved.append(place.label)
        except Exception as error:
            problems.append(f'Could not save to {place.label}: {error}')
    return {'saved': saved, 'problems': problems}
