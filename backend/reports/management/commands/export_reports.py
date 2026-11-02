"""Saves the three report PDFs for every finished 4-week block to Google Drive and/or a folder.

They are always saved in the project's report_exports folder. Extra copies come from settings (backend\.env):
REPORTS_EXPORT_DIR (e.g. a Google Drive for desktop folder), or GOOGLE_DRIVE_FOLDER_ID with
GOOGLE_SERVICE_ACCOUNT_FILE to upload to a Shared Drive. Run daily by a scheduled task
(scripts/export_reports.ps1). Blocks that already have their files are skipped, so running it every day is
safe, and a block missed while the PC was off is made the next time.
"""

from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from reports.destinations import GoogleDrive, LocalFolder
from reports.grids import REPORTS, corrective_rows
from reports.pdf import render_report

FIRST_BLOCK_START = date(2026, 11, 1)  # a Sunday: the first 4-week block of the paper sheets
BLOCK_DAYS = 28


def finished_blocks(today, include_current=False):
    """(start, end) of each 4-week block, Sunday to Saturday, that has ended (or is under way)."""
    start = FIRST_BLOCK_START
    while start <= today:
        end = start + timedelta(days=BLOCK_DAYS - 1)
        if end >= today and not include_current:
            return
        yield start, end
        start += timedelta(days=BLOCK_DAYS)


def file_name(kind, start, end):
    return f'{start} to {end} - {kind.capitalize()}.pdf'


class Command(BaseCommand):
    help = 'Save the report PDFs of each finished 4-week block to Google Drive and/or a folder.'

    def add_arguments(self, parser):
        parser.add_argument('--folder', help='Save into this folder instead of the settings (to test)')
        parser.add_argument('--include-current', action='store_true', help='Also save the block under way (to test)')
        parser.add_argument('--check', action='store_true', help='Only check that Google Drive can be reached')
        parser.add_argument('--today', help='Pretend today is this date (YYYY-MM-DD), for testing')

    def destinations(self, folder):
        if folder:
            return [LocalFolder(folder)]
        found = [LocalFolder(settings.REPORTS_LOCAL_DIR, create=True)]  # the permanent copy, inside the project
        if settings.GOOGLE_DRIVE_FOLDER_ID:
            if not settings.GOOGLE_SERVICE_ACCOUNT_FILE:
                raise CommandError('GOOGLE_SERVICE_ACCOUNT_FILE is not set in backend\.env.')
            found.append(GoogleDrive(settings.GOOGLE_DRIVE_FOLDER_ID, settings.GOOGLE_SERVICE_ACCOUNT_FILE))
        if settings.REPORTS_EXPORT_DIR:
            found.append(LocalFolder(settings.REPORTS_EXPORT_DIR))
        return found

    def handle(self, folder, include_current, check, today, **options):
        places = self.destinations(folder)
        if check:
            for place in places:
                if isinstance(place, GoogleDrive):
                    found = place.describe_folder()
                    self.stdout.write(f'OK: {place.account} can see the Drive folder "{found["name"]}".')
                else:
                    self.stdout.write(f'OK: {place.label}')
            return

        today = date.fromisoformat(today) if today else timezone.localdate()
        made = 0
        for start, end in finished_blocks(today, include_current):
            for kind, (heading, build_content) in REPORTS.items():
                name = file_name(kind, start, end)
                missing = [place for place in places if not place.has(name)]
                if not missing:
                    continue
                pdf = render_report(kind, heading, start, end, build_content(start, end), corrective_rows(start, end, kind))
                for place in missing:
                    place.save(name, pdf)
                    made += 1
                    self.stdout.write(f'Saved {name} to {place.label}')
        self.stdout.write(f'Done: {made} new PDF(s).')
