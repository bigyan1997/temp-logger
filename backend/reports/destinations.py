"""Places the exported report PDFs can be saved: a folder on this PC, or a Google Drive folder."""

from pathlib import Path

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
        # Written under a temporary name first, so a sync program never picks up half a file.
        target = self.folder / name
        partial = target.with_suffix('.tmp')
        partial.write_bytes(pdf)
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
        import json

        metadata = json.dumps({'name': name, 'parents': [self.folder_id]}).encode()
        body = (
            f'--{BOUNDARY}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n'.encode() + metadata
            + f'\r\n--{BOUNDARY}\r\nContent-Type: application/pdf\r\n\r\n'.encode() + pdf
            + f'\r\n--{BOUNDARY}--'.encode()
        )
        response = self.session.post(
            DRIVE_UPLOAD, params={'uploadType': 'multipart', 'supportsAllDrives': 'true', 'fields': 'id'},
            data=body, headers={'Content-Type': f'multipart/related; boundary={BOUNDARY}'},
        )
        self.check(response)
