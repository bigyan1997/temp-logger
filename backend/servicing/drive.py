"""Copies each attached invoice to Google Drive, in the same places as the non-conformance photos:

    <root folder>/Service Records/SVC-0001 - Coolroom/<file>

The file is always saved on this PC first, so a Drive problem never loses it. `copied_to` remembers which places
have it, so a retry only goes where it is missing."""

from nonconformance import photos
from nonconformance.drive import ROOT_FOLDER, clean, configured_labels, destinations

from .models import ServiceFile

SERVICE_FOLDER = 'Service Records'


def folder_name(service):
    return f'{service.number} - {clean(service.equipment)[:40]}'.rstrip(' -')


def copy_status(file):
    """off (no extra place is set up), saved (every place has it) or waiting."""
    labels = configured_labels()
    if not labels:
        return 'off'
    return 'saved' if set(labels) <= set(file.copied_to) else 'waiting'


def copy_file(file):
    """Copy one file to every place that does not have it yet. Never raises: the problem is kept on the file."""
    if not configured_labels():
        return
    places, problems = destinations()
    try:
        data = photos.full_path(file.path).read_bytes()
    except Exception as problem:
        file.copy_error = f'Could not copy yet: {problem}'[:300]
        file.save(update_fields=['copy_error'])
        return

    copied = list(file.copied_to)
    for place in places:
        if place.label in copied:
            continue
        try:
            place.save_in([ROOT_FOLDER, SERVICE_FOLDER, folder_name(file.service)], f'{file.pk}-{clean(file.original_name)[:100]}',
                          data, file.content_type)
            copied.append(place.label)
        except Exception as problem:
            problems.append(f'{place.label}: {problem}')
    file.copied_to = copied
    file.copy_error = '; '.join(problems)[:300]
    file.save(update_fields=['copied_to', 'copy_error'])


def copy_pending():
    """Try again for every file missing a copy (run every 5 minutes by send_alerts)."""
    labels = set(configured_labels())
    if not labels:
        return 0
    done = 0
    for file in ServiceFile.objects.select_related('service'):
        if labels <= set(file.copied_to):
            continue
        copy_file(file)
        file.refresh_from_db(fields=['copied_to'])
        done += labels <= set(file.copied_to)
    return done
