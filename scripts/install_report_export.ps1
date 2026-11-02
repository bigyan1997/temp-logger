# Makes the report PDFs save themselves into Google Drive: a task that runs every day at 3:30 am
# (and as soon as the PC is next on, if it was off). Run ONCE on the orders PC, in an ordinary
# PowerShell as the SAME Windows user that Google Drive for desktop is signed in under:
#     .\scripts\install_report_export.ps1
# (Run as that user, not SYSTEM: with Drive for desktop the synced folder belongs to that user.)
# Needs REPORTS_EXPORT_DIR in backend\.env (see docs/DEPLOYMENT.md). Safe to run again.

$root = Split-Path $PSScriptRoot -Parent
$task = 'Temperature Logger Report Export'

$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$PSScriptRoot\export_reports.ps1`"" `
    -WorkingDirectory $root
$daily = New-ScheduledTaskTrigger -Daily -At 3:30am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName $task -Action $action -Trigger $daily -Settings $settings -Force | Out-Null

Write-Host "Done. '$task' will run every day at 3:30 am as $env:USERNAME."
Write-Host "Try it now:  .\scripts\export_reports.ps1   (log: backend\logs\export_reports.log)"
