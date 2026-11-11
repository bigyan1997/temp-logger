# Auto-deploy: keeps the orders PC in step with GitHub, so code pushed from another
# computer goes live by itself. Run every 5 minutes by the scheduled task
# "Temperature Logger Auto Deploy" (made by install_autostart.ps1). Log:
# backend\logs\auto_deploy.log
#
# When main on GitHub has new commits, it:
#   1. fast-forwards this folder to them (never merges or overwrites work done
#      on this PC: with uncommitted changes or unpushed commits it skips and logs why);
#   2. installs Python/npm packages if their lists changed;
#   3. runs the tests and builds the frontend into a side folder while the live
#      app keeps running untouched;
#   4. only if all of that passes: migrates, swaps in the new frontend,
#      collects static files and restarts the server;
#   5. checks the app answers; if not, goes back to the previous commit.
# A failure before step 4 puts the previous commit back and leaves the live app alone.
# (deploy.ps1 does the same by hand, with output on screen.)

param(
    [string]$Remote = 'origin',
    [string]$Branch = 'main'
)

$root = Split-Path $PSScriptRoot -Parent
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$python = Join-Path $backend '.venv\Scripts\python.exe'
$logDir = Join-Path $backend 'logs'
$log = Join-Path $logDir 'auto_deploy.log'
$lock = Join-Path $logDir 'auto_deploy.lock'
$serverTask = 'Temperature Logger Server'

New-Item -ItemType Directory -Force $logDir | Out-Null
Set-Location $root  # scheduled tasks start in C:\Windows\System32
# The task runs as SYSTEM but the folder belongs to the Windows user, which git
# refuses ("dubious ownership") unless told this folder is safe.
$env:GIT_CONFIG_COUNT = '1'
$env:GIT_CONFIG_KEY_0 = 'safe.directory'
$env:GIT_CONFIG_VALUE_0 = $root -replace '\\', '/'

function Write-Log($message) {
    Add-Content -Path $log -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $message" -Encoding utf8
}

# Emails SYSTEM_ALERT_EMAIL (backend\.env) that a deploy failed, once per $key (the deploy retries every 5 minutes).
# Never stops the deploy: if email is not set up or the command is missing, it just carries on.
function Send-FailureEmail($subject, $message, $key) {
    try {
        Push-Location $backend
        & $python manage.py send_system_alert --kind deploy_failed --key $key $subject $message 2>&1 | Out-Null
    } catch {
        Write-Log "  (could not send the failure email: $_)"
    } finally {
        Pop-Location
    }
}

# Runs a command through cmd so its output is plain text. Returns the exit code;
# the output goes to the log only when the command fails.
function Invoke-Step($label, $command, $workdir = $root) {
    Push-Location $workdir
    try {
        $output = cmd /c "$command 2>&1"
        $code = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    if ($code -ne 0) {
        Write-Log "  FAILED: $label (exit $code)"
        $output | Select-Object -Last 40 | ForEach-Object { Write-Log "    $_" }
    }
    return $code
}

# Both the API and the page must answer (an API that is up does not prove the page is).
function Test-App {
    try {
        (Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8003/api/health/' -TimeoutSec 10).StatusCode -eq 200 -and
        (Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8003/' -TimeoutSec 10).StatusCode -eq 200
    } catch { $false }
}

function Restart-Server {
    Get-CimInstance Win32_Process |
        Where-Object { $_.CommandLine -match 'temp-logger\\scripts\\run_server\.bat' -or $_.CommandLine -match 'listen=0\.0\.0\.0:8003' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 3
    # Start it through its own task so it runs the same way as at boot (and logs to server.log).
    try { Start-ScheduledTask -TaskName $serverTask -ErrorAction Stop }
    catch { Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', "`"$PSScriptRoot\run_server.bat`"" -WorkingDirectory $root -WindowStyle Hidden }
    foreach ($i in 1..30) {
        Start-Sleep -Seconds 2
        if (Test-App) { return $true }
    }
    return $false
}

function Build-Frontend($changedFiles) {
    if ($changedFiles -match '^frontend/package(-lock)?\.json$') {
        if ((Invoke-Step 'npm install' 'npm.cmd install --no-audit --no-fund' $frontend) -ne 0) { return $false }
    }
    return (Invoke-Step 'frontend build' 'npm.cmd run build -- --outDir dist-next --emptyOutDir' $frontend) -eq 0
}

# Mirror the new build over dist with robocopy instead of delete-and-rename: an editor
# or virus scanner watching the folder can block a rename, which would leave no dist at all.
function Publish-Frontend {
    $dist = Join-Path $frontend 'dist'
    $next = Join-Path $frontend 'dist-next'
    & robocopy $next $dist /MIR /R:10 /W:2 /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8 -or -not (Test-Path (Join-Path $dist 'index.html'))) {
        Write-Log "  FAILED: copying the new frontend into place (robocopy exit $LASTEXITCODE)"
        return $false
    }
    Remove-Item -Recurse -Force $next -ErrorAction SilentlyContinue
    return (Invoke-Step 'collectstatic' "`"$python`" manage.py collectstatic --noinput" $backend) -eq 0
}

# One run at a time (a lock left by a crashed run expires after 30 minutes).
if ((Test-Path $lock) -and ((Get-Date) - (Get-Item $lock).LastWriteTime).TotalMinutes -lt 30) { exit 0 }
Set-Content -Path $lock -Value $PID

try {
    if ((Invoke-Step 'git fetch' "git fetch --quiet $Remote $Branch") -ne 0) { exit 1 }
    $old = (git rev-parse HEAD).Trim()
    $new = (git rev-parse FETCH_HEAD).Trim()
    if ($old -eq $new) { exit 0 }

    if (git status --porcelain --untracked-files=no) {
        Write-Log "Skipped $($new.Substring(0,7)): this folder has uncommitted changes. Commit and push (or discard) them to resume auto-deploy."
        exit 0
    }
    & git merge-base --is-ancestor $old $new
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Skipped $($new.Substring(0,7)): this PC has commits that are not on GitHub. Push them to resume auto-deploy."
        exit 0
    }

    $summary = (git log --format='%h %s' "$old..$new") -join ' | '
    Write-Log "Deploying $($old.Substring(0,7)) -> $($new.Substring(0,7)): $summary"
    $changed = git diff --name-only $old $new

    function Undo-Update($reason) {
        # Email first, while the new code (and the email command) is still in place.
        Send-FailureEmail "Auto-deploy failed: $reason" "Auto-deploy of $($new.Substring(0,7)) to the orders PC failed ($reason). The app stays on the previous version, $($old.Substring(0,7)). The change was: $summary. Details are in backend\logs\auto_deploy.log on the orders PC. It will keep trying every 5 minutes until the problem is fixed and pushed, but you will only get this email once." $new
        Write-Log "  Going back to $($old.Substring(0,7)) ($reason). The live app was not changed."
        & git reset --quiet --hard $old
        Remove-Item -Recurse -Force (Join-Path $frontend 'dist-next') -ErrorAction SilentlyContinue
        if ($changed -match '^backend/requirements\.txt$') {
            Invoke-Step 'restore python packages' "`"$python`" -m pip install -q -r requirements.txt" $backend | Out-Null
        }
    }

    if ((Invoke-Step 'git merge' "git merge --ff-only --quiet $new") -ne 0) { exit 1 }

    if ($changed -match '^backend/requirements\.txt$') {
        if ((Invoke-Step 'pip install' "`"$python`" -m pip install -q -r requirements.txt" $backend) -ne 0) {
            Undo-Update 'package install failed'; exit 1
        }
    }

    # The tests use their own throwaway Postgres database, never the real one.
    if ((Invoke-Step 'tests' "`"$python`" manage.py test --noinput" $backend) -ne 0) { Undo-Update 'tests failed'; exit 1 }

    $frontendChanged = [bool]($changed -match '^frontend/')
    if ($frontendChanged -and -not (Build-Frontend $changed)) { Undo-Update 'frontend build failed'; exit 1 }

    # --- from here on the live app changes ---
    if ((Invoke-Step 'migrate' "`"$python`" manage.py migrate --noinput" $backend) -ne 0) {
        Undo-Update 'database migration failed'; exit 1
    }
    if ($frontendChanged -and -not (Publish-Frontend)) {
        Write-Log '  WARNING: publishing the new frontend failed; the check below goes back if the page is down.'
    }

    if (Restart-Server) {
        Write-Log "  Deployed $($new.Substring(0,7)) - app is up."
        exit 0
    }

    Write-Log '  App did not come back after the restart - going back to the previous version.'
    Send-FailureEmail 'Auto-deploy: the app did not come back' "After deploying $($new.Substring(0,7)) the app did not answer, so it is going back to the previous version, $($old.Substring(0,7)). Details are in backend\logs\auto_deploy.log on the orders PC." "$new-down"
    & git reset --quiet --hard $old
    if ($frontendChanged -and (Build-Frontend $changed)) { Publish-Frontend | Out-Null }
    if (Restart-Server) {
        Write-Log "  Back on $($old.Substring(0,7)) - app is up. (A database migration from the failed version stays applied.)"
    } else {
        Write-Log '  ERROR: app still not answering after going back - needs a person to look at it.'
        Send-FailureEmail 'THE APP IS DOWN on the orders PC' "After a failed deploy the app is still not answering, even on the previous version. Someone needs to look at the orders PC. Details are in backend\logs\auto_deploy.log." "$new-stillDown"
    }
    exit 1
} catch {
    Write-Log "ERROR: auto-deploy stopped unexpectedly: $_"
    Send-FailureEmail 'Auto-deploy stopped unexpectedly' "Auto-deploy on the orders PC stopped with an error: $_. Details are in backend\logs\auto_deploy.log. You will get this email at most once a day." "unexpected-$(Get-Date -Format 'yyyy-MM-dd')"
    exit 1
} finally {
    Remove-Item -Path $lock -Force -ErrorAction SilentlyContinue
}
