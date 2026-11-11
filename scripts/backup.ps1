# Nightly backup of the Temperature Logger database. Records are never deleted,
# so the backups are what protects them if this PC fails.
#
# Run by a scheduled task every night (see docs/DEPLOYMENT.md). Reads the
# database settings from backend\.env. Writes a compressed pg_dump file to the
# backup folder and keeps:
#   - every daily backup for 30 days
#   - the first backup of each month, forever
#
# Usage: backup.ps1 [-BackupDir D:\Backups\temp-logger]
# Best practice: point the folder at a different drive. Set it as BACKUP_DIR in backend\.env (instead of
# -BackupDir) so the app can email you when a night's backup is missing.

param(
    [string]$BackupDir
)

$root = Split-Path $PSScriptRoot -Parent
$envFile = Join-Path $root 'backend\.env'
$logDir = Join-Path $root 'backend\logs'
$log = Join-Path $logDir 'backup.log'
$pgDump = Get-ChildItem 'C:\Program Files\PostgreSQL\*\bin\pg_dump.exe' | Sort-Object FullName -Descending | Select-Object -First 1

function Write-Log($message) {
    Add-Content -Path $log -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $message" -Encoding utf8
}

# Reads KEY=value lines from backend\.env
$settings = @{}
Get-Content $envFile | Where-Object { $_ -match '^\s*[A-Z_]+=' } | ForEach-Object {
    $key, $value = $_ -split '=', 2
    $settings[$key.Trim()] = $value.Trim()
}

# The folder comes from -BackupDir, else BACKUP_DIR in backend\.env (the app watches that same folder
# and emails if a day has no backup in it), else the project's backups folder.
if (-not $BackupDir) { $BackupDir = $settings['BACKUP_DIR'] }
if (-not $BackupDir) { $BackupDir = Join-Path $root 'backups' }

New-Item -ItemType Directory -Force $logDir, $BackupDir | Out-Null

if (-not $pgDump) { Write-Log 'FAILED: pg_dump.exe not found.'; exit 1 }

$stamp = Get-Date -Format 'yyyy-MM-dd'
$target = Join-Path $BackupDir "temp_logger_$stamp.dump"
$env:PGPASSWORD = $settings['DB_PASSWORD']
& $pgDump.FullName --host $settings['DB_HOST'] --port $settings['DB_PORT'] --username $settings['DB_USER'] `
    --format custom --file $target $settings['DB_NAME']

if ($LASTEXITCODE -ne 0 -or -not (Test-Path $target) -or (Get-Item $target).Length -lt 1KB) {
    Write-Log "FAILED: backup did not complete ($target)."
    exit 1
}
Write-Log "Backup written: $target ($([math]::Round((Get-Item $target).Length / 1KB)) KB)"

# Tidy up: keep daily backups for 30 days, and the first backup of every month forever.
function Remove-OldBackups($folder) {
    Get-ChildItem $folder -Filter 'temp_logger_*.dump' | Where-Object {
        $_.LastWriteTime -lt (Get-Date).AddDays(-30) -and $_.BaseName -notmatch 'temp_logger_\d{4}-\d{2}-01$'
    } | ForEach-Object {
        Remove-Item $_.FullName
        Write-Log "Removed old daily backup: $($_.Name)"
    }
}
Remove-OldBackups $BackupDir

# Report photos (non-conformance reports) are files, not database rows, so the dump does not include them. Copy the
# photos folder next to the backup. Photos are only ever added, so this never removes anything (no /MIR, no /PURGE).
$photos = $settings['NCR_PHOTOS_DIR']
if (-not $photos) { $photos = Join-Path $root 'ncr_photos' }
if (Test-Path $photos) {
    robocopy $photos (Join-Path $BackupDir 'ncr_photos') /E /XO /R:1 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { Write-Log "WARNING: copying the report photos failed (robocopy exit $LASTEXITCODE)." } else { Write-Log 'Report photos copied.' }
    $global:LASTEXITCODE = 0  # robocopy uses 1 to mean "files were copied"; that is not a failure of the backup
}

# Second copy in the Google Drive for desktop folder (BACKUP_DRIVE_DIR in backend\.env).
# Drive uploads it by itself. A failure here is logged but does not fail the backup,
# because the local copy above is already safe.
$driveDir = $settings['BACKUP_DRIVE_DIR']
if ($driveDir) {
    try {
        New-Item -ItemType Directory -Force $driveDir | Out-Null
        Copy-Item $target $driveDir -Force -ErrorAction Stop
        Write-Log "Copied to Google Drive folder: $driveDir"
        Remove-OldBackups $driveDir
    } catch {
        Write-Log "WARNING: could not copy to Google Drive folder ($driveDir): $_"
    }
}
