"""Keeps a second copy of every report photo where the report PDFs go: a Google Drive folder and/or a folder that
Google Drive for desktop keeps in sync (REPORTS_EXPORT_DIR and GOOGLE_DRIVE_FOLDER_ID in backend\\.env, see
reports/destinations.py).

The photo is always saved on this PC first, so a Drive problem never loses it or slows the page. Each place that
has a copy is remembered on the photo, so a retry only goes to the places that are missing (no duplicates)."""

import re
from pathlib import Path

from django.conf import settings

from reports.destinations import extra_destinations

from . import photos
from .models import Photo

ROOT_FOLDER = 'Non-Conformance Photos'


def configured_labels():
    """The names of the places photos should be copied to (the same labels reports/destinations.py gives them)."""
    labels = []
    if settings.GOOGLE_DRIVE_FOLDER_ID:
        labels.append(f'Google Drive folder {settings.GOOGLE_DRIVE_FOLDER_ID}')
    if settings.REPORTS_EXPORT_DIR:
        labels.append(str(Path(settings.REPORTS_EXPORT_DIR)))
    return labels


def drive_link():
    """A web address for the Drive folder the reports and photos go to, or '' when none is known."""
    if settings.GOOGLE_DRIVE_URL:
        return settings.GOOGLE_DRIVE_URL
    if settings.GOOGLE_DRIVE_FOLDER_ID:
        return f'https://drive.google.com/drive/folders/{settings.GOOGLE_DRIVE_FOLDER_ID}'
    return ''


def copy_status(photo):
    """off (no extra place is set up), saved (every place has it) or waiting."""
    labels = configured_labels()
    if not labels:
        return 'off'
    return 'saved' if set(labels) <= set(photo.copied_to) else 'waiting'


def clean(name):
    """Safe as a file or folder name in Windows and Drive."""
    return re.sub(r'\s+', ' ', re.sub(r'[\\/:*?"<>|]', ' ', name)).strip()


def folder_name(report):
    return f'{report.number} - {clean(report.product)[:40]}'.rstrip(' -')


def file_name(photo):
    return f'{photo.pk}-{clean(photo.original_name)[:100]}'


def copy_photo(photo):
    """Copy one photo to every place that does not have it yet. Never raises: the problem is kept on the photo."""
    if not configured_labels():
        return
    try:
        places = extra_destinations()
        data = photos.full_path(photo.path).read_bytes()
    except Exception as problem:  # Drive or its folder not reachable, or the file is gone from this PC
        photo.copy_error = f'Could not copy yet: {problem}'[:300]
        photo.save(update_fields=['copy_error'])
        return

    copied, problems = list(photo.copied_to), []
    for place in places:
        if place.label in copied:
            continue
        try:
            place.save_in([ROOT_FOLDER, folder_name(photo.report)], file_name(photo), data, photo.content_type)
            copied.append(place.label)
        except Exception as problem:
            problems.append(f'{place.label}: {problem}')
    photo.copied_to = copied
    photo.copy_error = '; '.join(problems)[:300]
    photo.save(update_fields=['copied_to', 'copy_error'])


def copy_pending():
    """Try again for every photo that is missing a copy (run every 5 minutes by send_alerts). Returns how many photos
    now have every copy."""
    labels = set(configured_labels())
    if not labels:
        return 0
    done = 0
    for photo in Photo.objects.filter(voided=False).select_related('report'):
        if labels <= set(photo.copied_to):
            continue
        copy_photo(photo)
        photo.refresh_from_db(fields=['copied_to'])
        done += labels <= set(photo.copied_to)
    return done
