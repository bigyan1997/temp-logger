"""Deleting a report (the owner allowed it on 2026-11-12, for reports made by mistake or while testing).

The report, its follow-ups and its photo rows are removed in one go and ONE audit line keeps what was deleted and why.
The photo files on this PC are removed, and the report's folder in the signed-in Google Drive goes to Drive's Bin
(recoverable for 30 days). Copies in other places (a synced folder, saved PDFs) are left alone."""

from django.db import transaction

from audit.models import AuditLog, record

from . import oauth_drive, photos
from .drive import folder_name


def delete_report(report, user, reason):
    """Returns a list of problems with the clean-up after the delete (an empty list means everything went well)."""
    updates, pictures = list(report.updates.all()), list(report.photos.all())
    paths = [photo.path for photo in pictures]
    folder = folder_name(report)
    summary = (f'Deleted report {report.number}: {report.product} (customer {report.customer or "-"}, dated {report.date:%d/%m/%Y}; '
               f'{len(updates)} follow-up(s), {len(pictures)} photo(s))')
    with transaction.atomic():
        report.photos.all().delete()
        report.updates.all().delete()
        report.delete()
        record(user, AuditLog.Action.DELETED, summary, reason, module=AuditLog.Module.NONCONFORMANCE)

    problems = []
    for path in paths:
        try:
            photos.full_path(path).unlink(missing_ok=True)
        except Exception as problem:
            problems.append(f'A photo file could not be removed from this computer: {problem}')
    if oauth_drive.enabled():
        try:
            oauth_drive.OAuthDrive().trash_folder(folder)
        except Exception as problem:
            problems.append(f'The Google Drive folder could not be moved to the Bin, delete it by hand: {problem}')
    return problems
