# Makes the Temperature Logger start by itself when the computer turns on, and stay up.
# Run ONCE on the orders PC, in PowerShell opened with "Run as administrator":
#     .\scripts\install_autostart.ps1
# Safe to run again; it replaces the tasks it made before. See docs/DEPLOYMENT.md.
#
#   Server task     starts at boot (no one needs to log in), runs hidden as SYSTEM,
#                   has no time limit and is restarted by Windows if it ever stops.
#   Keep-alive task every 5 minutes, restarts the server if it stops answering.
#   Power           the PC never goes to sleep while plugged in.

#Requires -RunAsAdministrator

$root = Split-Path $PSScriptRoot -Parent
$logDir = Join-Path $root 'backend\logs'
New-Item -ItemType Directory -Force $logDir | Out-Null

$asSystem = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest

# --- The server: starts at boot, restarts if it stops ---
$serverTask = 'Temperature Logger Server'
$serverAction = New-ScheduledTaskAction -Execute 'cmd.exe' `
    -Argument "/c `"`"$PSScriptRoot\run_server.bat`" >> `"$logDir\server.log`" 2>&1`"" -WorkingDirectory $root
$atBoot = New-ScheduledTaskTrigger -AtStartup
$atBoot.Delay = 'PT30S'  # let PostgreSQL and the network come up first
$serverSettings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $serverTask -Action $serverAction -Trigger $atBoot `
    -Settings $serverSettings -Principal $asSystem -Force | Out-Null

# --- The watchdog: every 5 minutes ---
$watchTask = 'Temperature Logger Keep Alive'
$watchAction = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\keep_alive.ps1`"" -WorkingDirectory $root
$everyFive = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5)
$watchSettings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $watchTask -Action $watchAction -Trigger $everyFive `
    -Settings $watchSettings -Principal $asSystem -Force | Out-Null

# --- Never sleep while plugged in (0 = never) ---
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0

# Start the server now instead of waiting for the next boot.
Start-ScheduledTask -TaskName $serverTask
Write-Host "Done. '$serverTask' and '$watchTask' are installed and the server is starting."
Write-Host "Check in a minute: http://localhost:8003   (log: $logDir\server.log)"
