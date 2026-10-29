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
# Best practice: point -BackupDir at a different drive or a synced cloud folder.

param(
    [string]$BackupDir = (Join-Path (Split-Path $PSScriptRoot -Parent) 'backups')
)

$root = Split-Path $PSScriptRoot -Parent
$envFile = Join-Path $root 'backend\.env'
$logDir = Join-Path $root 'backend\logs'
$log = Join-Path $logDir 'backup.log'
$pgDump = Get-ChildItem 'C:\Program Files\PostgreSQL\*\bin\pg_dump.exe' | Sort-Object FullName -Descending | Select-Object -First 1

New-Item -ItemType Directory -Force $logDir, $BackupDir | Out-Null

function Write-Log($message) {
    Add-Content -Path $log -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $message" -Encoding utf8
}

# Reads KEY=value lines from backend\.env
$settings = @{}
Get-Content $envFile | Where-Object { $_ -match '^\s*[A-Z_]+=' } | ForEach-Object {
    $key, $value = $_ -split '=', 2
    $settings[$key.Trim()] = $value.Trim()
}

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
Get-ChildItem $BackupDir -Filter 'temp_logger_*.dump' | Where-Object {
    $_.LastWriteTime -lt (Get-Date).AddDays(-30) -and $_.BaseName -notmatch 'temp_logger_\d{4}-\d{2}-01$'
} | ForEach-Object {
    Remove-Item $_.FullName
    Write-Log "Removed old daily backup: $($_.Name)"
}
