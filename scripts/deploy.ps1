# Updates the running app on the orders PC to the latest code from GitHub.
# Run it by hand in PowerShell:   .\scripts\deploy.ps1
#
# It stops straight away if anything fails, so a broken update never replaces
# a working app. Steps: pull, install packages, run the tests, build the
# frontend into a side folder, migrate the database, swap in the new frontend,
# collect static files, restart the server.

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$python = Join-Path $backend '.venv\Scripts\python.exe'

function Step($message) { Write-Host "`n== $message" -ForegroundColor Cyan }

function Run($command) {
    cmd /c "$command 2>&1"
    if ($LASTEXITCODE -ne 0) { throw "Failed: $command" }
}

Set-Location $root

Step 'Pulling the latest code'
Run 'git pull --ff-only'

Step 'Installing Python packages'
Run "`"$python`" -m pip install -q -r backend\requirements.txt"

Step 'Running the tests'
Push-Location $backend
Run "`"$python`" manage.py test --noinput"
Pop-Location

Step 'Building the frontend (into a side folder, so the live app keeps working)'
Push-Location $frontend
Run 'npm install --silent'
Run 'npx vite build --outDir dist-next --emptyOutDir'
Pop-Location

Step 'Migrating the database'
Push-Location $backend
Run "`"$python`" manage.py migrate --noinput"
Pop-Location

Step 'Swapping in the new frontend'
if (Test-Path (Join-Path $frontend 'dist')) { Remove-Item (Join-Path $frontend 'dist') -Recurse -Force }
Rename-Item (Join-Path $frontend 'dist-next') 'dist'

Step 'Collecting static files'
Push-Location $backend
Run "`"$python`" manage.py collectstatic --noinput"
Pop-Location

Step 'Restarting the server'
Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -match 'temp-logger\\scripts\\run_server\.bat' -or $_.CommandLine -match 'listen=0\.0\.0\.0:8003' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 3
Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', "`"$PSScriptRoot\run_server.bat`"" -WorkingDirectory $root -WindowStyle Minimized

foreach ($attempt in 1..30) {
    Start-Sleep -Seconds 2
    try {
        if ((Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8003/api/health/' -TimeoutSec 5).StatusCode -eq 200) {
            Write-Host "`nDone. The Temperature Logger is running on port 8003." -ForegroundColor Green
            exit 0
        }
    } catch { }
}
throw 'The server did not come back up. Check backend\logs and run scripts\run_server.bat by hand to see the error.'
