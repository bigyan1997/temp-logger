"""Google Drive for non-conformance reports, signed in as a real Google account (the same way the npd-tracker and
fleet-maintenance apps do it). Photos and report PDFs are uploaded straight to that account's Drive, one folder per
report, and the folders are made automatically:

    <NCR_DRIVE_ROOT_FOLDER>/NCR-0001 - <product>/<photos and the report PDF>

Turned on by running `python manage.py drive_authorize` once, which saves a sign-in token in backend/secrets
(gitignored). Without that token this does nothing and the other copy places (reports/destinations.py) still work."""

from pathlib import Path

from django.conf import settings

from reports.destinations import DRIVE_FILES, DRIVE_SCOPE, GoogleDrive

LABEL = 'Google Drive (signed-in account)'
_root_id = None  # looked up once, then remembered


def token_path():
    return Path(settings.BASE_DIR) / settings.NCR_DRIVE_TOKEN_FILE


def client_path():
    return Path(settings.BASE_DIR) / settings.NCR_DRIVE_CLIENT_FILE


def enabled():
    return bool(settings.NCR_DRIVE_TOKEN_FILE) and token_path().is_file()


class OAuthDrive(GoogleDrive):
    """Uses the signed-in account's own Drive; the root folder is made in My Drive the first time."""

    def __init__(self):
        # Imported here so the rest of the app works without the Google packages.
        from google.auth.transport.requests import AuthorizedSession
        from google.oauth2.credentials import Credentials

        credentials = Credentials.from_authorized_user_file(str(token_path()), [DRIVE_SCOPE])
        self.session = AuthorizedSession(credentials)  # refreshes the access token by itself
        self.label = LABEL
        self.folder_id = self.root_id()

    def save_in(self, subfolders, name, data, content_type='application/pdf'):
        # This account's root folder already is the reports folder, so the first name is not made again inside it.
        if subfolders and subfolders[0] == settings.NCR_DRIVE_ROOT_FOLDER:
            subfolders = subfolders[1:]
        super().save_in(subfolders, name, data, content_type)

    def trash_folder(self, name):
        """Move the report's folder to Drive's Bin (recoverable for 30 days). Nothing happens if it is not there."""
        escaped = name.replace('\\', '\\\\').replace("'", "\\'")
        found = self.check(self.session.get(DRIVE_FILES, params={
            'q': f"name = '{escaped}' and '{self.folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
            'fields': 'files(id)',
        }))['files']
        for folder in found:
            self.check(self.session.patch(f'{DRIVE_FILES}/{folder["id"]}', params={'supportsAllDrives': 'true'}, json={'trashed': True}))

    def root_id(self):
        global _root_id
        if _root_id is None:
            _root_id = self.folder_in('root', settings.NCR_DRIVE_ROOT_FOLDER)
        return _root_id


def folder_url():
    """The web address of the root folder, or '' when Drive is not signed in or cannot be reached right now."""
    if not enabled():
        return ''
    try:
        return f'https://drive.google.com/drive/folders/{OAuthDrive().folder_id}'
    except Exception:
        return ''
