"""Saves a PDF of a report where the other report PDFs go: always the project's report_exports folder, plus the
Google Drive folder or synced folder from settings (reports/destinations.py)."""

from django.conf import settings
from django.utils import timezone

from reports.destinations import LocalFolder, extra_destinations

from .drive import clean
from .pdf import render_report

SUBFOLDER = 'Non-Conformance Reports'


def file_name(report):
    # The time is in the name: a report grows with follow-ups, so each save is a new dated file and never overwrites one.
    return f'{report.number} - {clean(report.product)[:40]} - {timezone.localtime():%Y-%m-%d %H%M}.pdf'


def save_report_copies(report):
    """Never raises. Returns {'saved': [where, ...], 'problems': [text, ...], 'name': file name}."""
    saved, problems = [], []
    name = file_name(report)
    try:
        pdf = render_report(report)
    except Exception as error:
        return {'saved': [], 'problems': [f'The PDF could not be made: {error}'], 'name': name}

    places = []
    try:
        places.append(LocalFolder(settings.REPORTS_LOCAL_DIR, create=True))
    except Exception as error:
        problems.append(f'The copy on this computer could not be saved: {error}')
    try:
        places += extra_destinations()
    except Exception as error:
        problems.append(f'Google Drive could not be reached: {error}')

    for place in places:
        try:
            place.save_in([SUBFOLDER], name, pdf, 'application/pdf')
            saved.append(place.label)
        except Exception as error:
            problems.append(f'Could not save to {place.label}: {error}')
    return {'saved': saved, 'problems': problems, 'name': name}
