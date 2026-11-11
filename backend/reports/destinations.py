"""Places the exported report PDFs can be saved: a folder on this PC, or a Google Drive folder."""

from pathlib import Path

from django.conf import settings
from django.core.management.base import CommandError

DRIVE_FILES = 'https://www.googleapis.com/drive/v3/files'
DRIVE_UPLOAD = 'https://www.googleapis.com/upload/drive/v3/files'
DRIVE_SCOPE = 'https://www.googleapis.com/auth/drive'
BOUNDARY = 'report-upload-boundary'


class LocalFolder:
    """A normal folder, e.g. one that Google Drive for desktop keeps in sync."""

    def __init__(self, folder, create=False):
        self.folder = Path(folder)
        if create:
            self.folder.mkdir(parents=True, exist_ok=True)
        if not self.folder.is_dir():
            raise CommandError(f'The folder does not exist: {self.folder}. Is Google Drive for desktop running?')
        self.label = str(self.folder)

    def has(self, name):
        return (self.folder / name).exists()

    def save(self, name, pdf):
        self.save_in([], name, pdf)

    def save_in(self, subfolders, name, data, content_type=None):
        """Save a file inside subfolders (made if they are not there yet), e.g. ['Non-Conformance Photos', 'NCR-0001']."""
        folder = self.folder.joinpath(*subfolders)
        folder.mkdir(parents=True, exist_ok=True)
        # Written under a temporary name first, so a sync program never picks up half a file.
        target = folder / name
        partial = target.with_name(target.name + '.tmp')
        partial.write_bytes(data)
        partial.replace(target)


class GoogleDrive:
    """A Google Drive folder, reached with a service account that the folder has been shared with."""

    def __init__(self, folder_id, key_file):
        # Imported here so the rest of the app works without the Google packages.
        from google.auth.transport.requests import AuthorizedSession
        from google.oauth2 import service_account

        if not Path(key_file).is_file():
            raise CommandError(f'The Google key file was not found: {key_file}')
        credentials = service_account.Credentials.from_service_account_file(key_file, scopes=[DRIVE_SCOPE])
        self.session = AuthorizedSession(credentials)
        self.folder_id = folder_id
        self.account = credentials.service_account_email
        self.label = f'Google Drive folder {folder_id}'

    def check(self, response):
        if not response.ok:
            try:
                message = response.json()['error']['message']
            except (ValueError, KeyError):
                message = response.text[:200]
            raise CommandError(f'Google Drive said no ({response.status_code}): {message}')
        return response.json()

    def describe_folder(self):
        """The folder's name, to prove the service account can see it."""
        response = self.session.get(
            f'{DRIVE_FILES}/{self.folder_id}', params={'fields': 'id,name,mimeType', 'supportsAllDrives': 'true'}
        )
        return self.check(response)

    def has(self, name):
        escaped = name.replace("'", "\'")
        response = self.session.get(DRIVE_FILES, params={
            'q': f"name = '{escaped}' and '{self.folder_id}' in parents and trashed = false",
            'fields': 'files(id)', 'supportsAllDrives': 'true', 'includeItemsFromAllDrives': 'true',
        })
        return bool(self.check(response)['files'])

    def save(self, name, pdf):
        self.save_in([], name, pdf, 'application/pdf')

    def folder_in(self, parent_id, name):
        """The id of the folder called `name` inside `parent_id`, made if it is not there yet."""
        escaped = name.replace('\\', '\\\\').replace("'", "\\'")
        found = self.check(self.session.get(DRIVE_FILES, params={
            'q': f"name = '{escaped}' and '{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
            'fields': 'files(id)', 'supportsAllDrives': 'true', 'includeItemsFromAllDrives': 'true',
        }))['files']
        if found:
            return found[0]['id']
        made = self.session.post(
            DRIVE_FILES, params={'supportsAllDrives': 'true', 'fields': 'id'},
            json={'name': name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]},
        )
        return self.check(made)['id']

    def save_in(self, subfolders, name, data, content_type='application/pdf'):
        """Save a file inside subfolders of the Drive folder (made if they are not there yet)."""
        import json

        parent = self.folder_id
        for subfolder in subfolders:
            parent = self.folder_in(parent, subfolder)
        metadata = json.dumps({'name': name, 'parents': [parent]}).encode()
        body = (
            f'--{BOUNDARY}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n'.encode() + metadata
            + f'\r\n--{BOUNDARY}\r\nContent-Type: {content_type}\r\n\r\n'.encode() + data
            + f'\r\n--{BOUNDARY}--'.encode()
        )
        response = self.session.post(
            DRIVE_UPLOAD, params={'uploadType': 'multipart', 'supportsAllDrives': 'true', 'fields': 'id'},
            data=body, headers={'Content-Type': f'multipart/related; boundary={BOUNDARY}'},
        )
        self.check(response)


def extra_destinations():
    """The optional extra copies named in settings (backend\\.env): a Google Drive folder and/or a synced folder."""
    found = []
    if settings.GOOGLE_DRIVE_FOLDER_ID:
        if not settings.GOOGLE_SERVICE_ACCOUNT_FILE:
            raise CommandError('GOOGLE_SERVICE_ACCOUNT_FILE is not set in backend\\.env.')
        found.append(GoogleDrive(settings.GOOGLE_DRIVE_FOLDER_ID, settings.GOOGLE_SERVICE_ACCOUNT_FILE))
    if settings.REPORTS_EXPORT_DIR:
        found.append(LocalFolder(settings.REPORTS_EXPORT_DIR))
    return found
