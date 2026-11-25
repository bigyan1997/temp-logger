"""Deleting a service record or one of its files (the owner chose this on 2026-11-25, in place of voiding).

The record, its file rows and its audit trail are handled in one go: ONE audit line keeps what was deleted and why.
The files on this PC are removed. For a whole record, its folder in the signed-in Google Drive goes to Drive's Bin
(recoverable for 30 days). A single deleted file's Drive copy is left where it is, and the problems list says so."""

from django.db import transaction

from audit.models import AuditLog, record
from nonconformance import oauth_drive, photos

from .drive import SERVICE_FOLDER, folder_name


def remove_from_pc(paths):
    problems = []
    for path in paths:
        try:
            photos.full_path(path).unlink(missing_ok=True)
        except Exception as problem:
            problems.append(f'A file could not be removed from this computer: {problem}')
    return problems


def delete_record(service, user, reason, person):
    """Returns a list of problems with the clean-up after the delete (an empty list means everything went well)."""
    files = list(service.files.all())
    folder = folder_name(service)
    summary = (f'Deleted {service.number}: {service.equipment}, serviced by {service.serviced_by} on {service.service_date:%d/%m/%Y} '
               f'(invoice {service.invoice_number or "-"}; {len(files)} file(s))')
    with transaction.atomic():
        service.files.all().delete()
        service.delete()
        record(user, AuditLog.Action.DELETED, summary, reason, module=AuditLog.Module.SERVICING, staff=person)

    problems = remove_from_pc([f.path for f in files])
    if oauth_drive.enabled():
        try:
            oauth_drive.OAuthDrive().trash_folder(folder)  # the folder is inside the Service Records folder
        except Exception as problem:
            problems.append(f'The Google Drive folder {SERVICE_FOLDER}/{folder} could not be moved to the Bin, delete it by hand: {problem}')
    return problems


def delete_file(file, user, reason, person):
    summary = f'Deleted file {file.original_name} from {file.service.number}'
    path = file.path
    with transaction.atomic():
        file.delete()
        record(user, AuditLog.Action.DELETED, summary, reason, module=AuditLog.Module.SERVICING, staff=person)
    problems = remove_from_pc([path])
    if file.copied_to:
        problems.append('Its copy in Google Drive was left there, delete it by hand if it should go too.')
    return problems
