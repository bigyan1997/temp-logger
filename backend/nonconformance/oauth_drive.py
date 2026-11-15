"""Google Drive for non-conformance reports, signed in as a real Google account (the same way the npd-tracker and
fleet-maintenance apps do it). Photos and report PDFs are uploaded straight to that account's Drive, one folder per
report, and the folders are made automatically:

    <NCR_DRIVE_ROOT_FOLDER>/NCR-0001 - <product>/<photos and the report PDF>

On a test computer (DRIVE_TEST_MODE) the root folder is "TEST - <NCR_DRIVE_ROOT_FOLDER>" instead.

Turned on by running `python manage.py drive_authorize` once, which saves a sign-in token in backend/secrets
(gitignored). Without that token this does nothing and the other copy places (reports/destinations.py) still work."""

from pathlib import Path

from django.conf import settings

from reports.destinations import DRIVE_FILES, DRIVE_SCOPE, GoogleDrive

LABEL = 'Google Drive (signed-in account)'
TEST_LABEL = 'Google Drive TEST folder (signed-in account)'  # a different label, so a test copy never counts as the live one
REPORT_ROOT = 'Non-Conformance Reports'  # the name the rest of the app puts first; this account's root folder replaces it
_root_ids = {}  # folder name -> its id, looked up once and then remembered


def label():
    return TEST_LABEL if settings.DRIVE_TEST_MODE else LABEL


def ncr_root_name():
    """The Drive folder the reports go in. In test mode it starts with "TEST - ", so it is never the live one."""
    prefix = settings.DRIVE_TEST_PREFIX if settings.DRIVE_TEST_MODE else ''
    return prefix + settings.NCR_DRIVE_ROOT_FOLDER


def token_path():
    return Path(settings.BASE_DIR) / settings.NCR_DRIVE_TOKEN_FILE


def client_path():
    return Path(settings.BASE_DIR) / settings.NCR_DRIVE_CLIENT_FILE


def enabled():
    return bool(settings.NCR_DRIVE_TOKEN_FILE) and token_path().is_file()


class OAuthDrive(GoogleDrive):
    """Uses the signed-in account's own Drive; the root folder is made in My Drive the first time.
    `root_name` is another folder to use instead of the non-conformance one (the test-mode report PDFs)."""

    def __init__(self, root_name=None):
        # Imported here so the rest of the app works without the Google packages.
        from google.auth.transport.requests import AuthorizedSession
        from google.oauth2.credentials import Credentials

        credentials = Credentials.from_authorized_user_file(str(token_path()), [DRIVE_SCOPE])
        self.session = AuthorizedSession(credentials)  # refreshes the access token by itself
        self.root_name = root_name or ncr_root_name()
        self.label = label() if root_name is None else f'Google Drive folder "{root_name}"'
        self.folder_id = self.root_id()

    def save_in(self, subfolders, name, data, content_type='application/pdf'):
        # This account's root folder already is the reports folder, so the first name is not made again inside it.
        # (Whatever the root folder is called: the live one is "Achieve HACCP - ...", a test one starts with "TEST - ".)
        if subfolders and subfolders[0] == REPORT_ROOT:
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
        if self.root_name not in _root_ids:
            _root_ids[self.root_name] = self.folder_in('root', self.root_name)
        return _root_ids[self.root_name]


def folder_url():
    """The web address of the root folder, or '' when Drive is not signed in or cannot be reached right now."""
    if not enabled():
        return ''
    try:
        return f'https://drive.google.com/drive/folders/{OAuthDrive().folder_id}'
    except Exception:
        return ''
