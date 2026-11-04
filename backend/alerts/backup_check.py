"""Checks that last night's database backup (scripts/backup.ps1) really happened.

It looks at the backup folder instead of trusting the script, so it also catches the cases where the script
never ran at all (PC off, task removed, task running as the wrong user)."""

from datetime import datetime, timezone as utc
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from .checks import Alert

# The backup task runs at 2 am. Waiting until 6 am leaves time for a PC that was off to catch up first.
CHECK_FROM_HOUR = 6
MIN_DUMP_BYTES = 1024  # backup.ps1 treats anything smaller as a failed backup


def good_dumps(folder):
    return [path for path in folder.glob('temp_logger_*.dump') if path.stat().st_size >= MIN_DUMP_BYTES]


def local_day(path):
    return timezone.localtime(datetime.fromtimestamp(path.stat().st_mtime, tz=utc.utc)).date()


def missed_backup(now):
    """An alert (at most one per day) when today has no backup yet. Nothing when BACKUP_DIR is not set."""
    if not settings.BACKUP_DIR:
        return []
    today = timezone.localtime(now)
    if today.hour < CHECK_FROM_HOUR:
        return []

    folder = Path(settings.BACKUP_DIR)
    dumps = good_dumps(folder) if folder.is_dir() else []
    if any(local_day(path) == today.date() for path in dumps):
        return []

    last = max((local_day(path) for path in dumps), default=None)
    last_text = f'The last good backup was on {last:%A %d %B %Y}.' if last else 'No backup has been found at all.'
    lead = f"Last night's database backup did not happen. {last_text}"
    return [Alert(
        'backup', today.date().isoformat(), 'DATABASE BACKUP FAILED',
        f"{lead}\nCheck backend\\logs\\backup.log on the orders PC.", lead=lead, tone='failed',
    )]
