"""Keeps a second copy of every report photo where the report PDFs go: a Google Drive folder and/or a folder that
Google Drive for desktop keeps in sync (REPORTS_EXPORT_DIR and GOOGLE_DRIVE_FOLDER_ID in backend\\.env, see
reports/destinations.py).

The photo is always saved on this PC first, so a Drive problem never loses it or slows the page. Each place that
has a copy is remembered on the photo, so a retry only goes to the places that are missing (no duplicates)."""

import re
from pathlib import Path

from django.conf import settings

from reports.destinations import extra_destinations

from . import oauth_drive, photos
from .models import Photo

# One folder per report, holding its photos and its PDF: <ROOT_FOLDER>/NCR-0001 - <product>/
ROOT_FOLDER = 'Non-Conformance Reports'


def configured_labels():
    """The names of the places photos should be copied to (the same labels reports/destinations.py gives them)."""
    labels = []
    if settings.GOOGLE_DRIVE_FOLDER_ID:
        labels.append(f'Google Drive folder {settings.GOOGLE_DRIVE_FOLDER_ID}')
    if settings.REPORTS_EXPORT_DIR:
        labels.append(str(Path(settings.REPORTS_EXPORT_DIR)))
    if oauth_drive.enabled():
        labels.append(oauth_drive.LABEL)
    return labels


def destinations():
    """Every place a copy should go, and the problems finding them (one place failing must not stop the others)."""
    places, problems = [], []
    for make in (extra_destinations, lambda: [oauth_drive.OAuthDrive()] if oauth_drive.enabled() else []):
        try:
            places += make()
        except Exception as problem:
            problems.append(f'Google Drive could not be reached: {problem}')
    return places, problems


def drive_link():
    """A web address for the Drive folder the reports and photos go to, or '' when none is known."""
    if settings.GOOGLE_DRIVE_URL:
        return settings.GOOGLE_DRIVE_URL
    if oauth_drive.enabled():
        return oauth_drive.folder_url()
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
    places, problems = destinations()
    try:
        data = photos.full_path(photo.path).read_bytes()
    except Exception as problem:  # the file is gone from this PC
        photo.copy_error = f'Could not copy yet: {problem}'[:300]
        photo.save(update_fields=['copy_error'])
        return

    copied = list(photo.copied_to)
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
