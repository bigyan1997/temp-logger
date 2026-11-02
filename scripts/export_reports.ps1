# Saves the report PDFs of each finished 4-week block to Google Drive and/or a folder.
# Where they go is set in backend\.env (GOOGLE_DRIVE_FOLDER_ID + GOOGLE_SERVICE_ACCOUNT_FILE, and/or
# REPORTS_EXPORT_DIR). Run daily by the "Temperature Logger Report Export" task (see install_report_export.ps1).
# Blocks already saved are skipped, so a missed day is made up the next time it runs.
# Log: backend\logs\export_reports.log

$root = Split-Path $PSScriptRoot -Parent
$logDir = Join-Path $root 'backend\logs'
$log = Join-Path $logDir 'export_reports.log'
New-Item -ItemType Directory -Force $logDir | Out-Null

Set-Location (Join-Path $root 'backend')
$output = & .\.venv\Scripts\python.exe manage.py export_reports 2>&1
$status = if ($LASTEXITCODE -eq 0) { 'OK' } else { 'FAILED' }
Add-Content -Path $log -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  ${status}: $($output -join ' | ')" -Encoding utf8
exit $LASTEXITCODE
