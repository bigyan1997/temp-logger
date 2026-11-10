# Deploying to the orders PC

The app runs on the office orders PC (Windows) on **port 8003**, using Waitress, next to the other apps that use ports 8000 to 8002. Staff reach it on the office network at `http://<orders-pc-address>:8003`, or from home over Tailscale.

Keep real addresses, passwords and keys out of the repo. Put them in `backend\.env` and in a local `DEPLOYMENT_NOTES.md` (both are gitignored).

## First-time setup

1. **Install** (if not already there): Git, Python 3.14, Node.js, PostgreSQL.
2. **Get the code**
   ```
   cd C:\Users\<you>
   git clone https://github.com/bigyan1997/temp-logger.git
   cd temp-logger
   ```
3. **Create the database** (pgAdmin Query Tool, one statement at a time, with your own password):
   ```sql
   CREATE ROLE temp_logger LOGIN PASSWORD 'choose-a-password' CREATEDB;
   ```
   ```sql
   CREATE DATABASE temp_logger OWNER temp_logger;
   ```
4. **Backend**
   ```
   cd backend
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   copy .env.example .env
   ```
   Edit `.env`: set `DB_PASSWORD`, a long random `DJANGO_SECRET_KEY`, and:
   ```
   DJANGO_DEBUG=False
   DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,<orders-pc-name-or-address>,<tailscale-address>
   CSRF_TRUSTED_ORIGINS=http://<orders-pc-name-or-address>:8003,http://<tailscale-address>:8003
   ```
   Then:
   ```
   python manage.py migrate
   python manage.py create_default_logins --password "<a-strong-password>"
   ```
   `migrate` also adds the default storage units, suppliers and runs, and the database protections that stop records being deleted. `create_default_logins` makes `admin@achievecafeprovisions.com.au` and `night@achievecafeprovisions.com.au`. Logins are data, so they must be created on this database; they do not come from GitHub.
5. **Frontend**
   ```
   cd ..\frontend
   npm install
   npm run build
   cd ..\backend
   python manage.py collectstatic --noinput
   ```
6. **Try it**: `scripts\run_server.bat`, then open `http://localhost:8003` on that PC.
7. **Let the office reach it**: allow port 8003 through Windows Firewall (PowerShell as Administrator):
   ```
   New-NetFirewallRule -DisplayName "Temperature Logger 8003" -Direction Inbound -Protocol TCP -LocalPort 8003 -Action Allow -Profile Private
   ```
8. **Start at boot and stay up** (PowerShell opened with *Run as administrator*, from the repo folder):
   ```
   .\scripts\install_autostart.ps1
   ```
   This starts the server whenever the PC turns on (nobody has to log in), restarts it if it stops, checks every 5 minutes that it still answers, and stops the PC sleeping while plugged in. It is safe to run again. Log: `backend\logs\server.log`.
9. **After a reboot**: restart the PC once and open `http://localhost:8003` after about a minute to confirm it came back by itself. (Also set Windows Update "active hours" so it does not restart in the middle of the day. When it does restart, the server comes back by itself.)
10. **Nightly backup** (2 am). Each night `scripts\backup.ps1` writes a pg_dump into a local folder and copies it into Google Drive, so there are two copies (30 daily backups kept, plus the first of each month forever, in both places). Both folders are set in `backend\.env`, not in the task:
    ```
    BACKUP_DIR=C:\Users\<you>\Desktop\Temp-Logger\backups
    BACKUP_DRIVE_DIR=G:\My Drive\Temp Logger Backups
    ```
    - `BACKUP_DIR` is the local copy (a different drive is better if the PC has one). Setting it also turns on the **missed-backup email**: from 6 am the alerts task checks the folder has a backup from today (over 1 KB); if not, it emails everyone under *Settings, Alert emails* once that day ("DATABASE BACKUP FAILED", with the date of the last good one). This also catches the PC being off or the task not running. Nothing is sent while `BACKUP_DIR` is empty.
    - `BACKUP_DRIVE_DIR` is a folder inside Google Drive for desktop (install it, sign in; the orders PC uses the default **Stream files** `G:\My Drive` and that works). Drive uploads the copy by itself. If the copy fails, `backend\logs\backup.log` shows a WARNING and the local backup still counts. The dump holds all records, so keep that Drive account private.
    - Do **not** point `-BackupDir` at the Drive folder: then there is no local copy, and with `BACKUP_DIR` set the missed-backup email goes off every day.

    Create the task in PowerShell **as Administrator** (it runs as your own Windows user, because Drive only runs while that user is logged in; locking the screen is fine, signing out is not):
    ```
    $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$PWD\scripts\backup.ps1`""
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName 'Temperature Logger Backup' -Action $action -Trigger (New-ScheduledTaskTrigger -Daily -At 2am) -Settings $settings -Force
    ```
    `-StartWhenAvailable` makes a night missed while the PC was off or logged out run as soon as it can. Then run `.\scripts\backup.ps1` once by hand and check `backend\logs\backup.log` says "Backup written" and "Copied to Google Drive folder". **Test a restore before relying on it** (see below).

11. **Alert emails.** Every 5 minutes (the task `install_autostart.ps1` makes) the app emails the people under *Settings, Alert emails* when: a storage reading is still not logged shortly before it is due (**first reminder 30 minutes before**: 8:30 am for the 9 am readings, 8:30 pm for 9 pm, 2:30 pm for Friday 3 pm) and still not logged **3 hours after** (**second reminder**: 12 pm, 12 am, 6 pm). Only these storage reminders are emailed (not out-of-limit readings or corrective actions). A reminder lists only the units still missing and is not sent if everything is logged. Each alert is sent once, and *Settings, Alert emails* lists the ones already sent (last 100). To send real email, put the sending account in `backend\.env`: `EMAIL_HOST` (for Gmail `smtp.gmail.com`, for Microsoft 365 `smtp.office365.com`), `EMAIL_PORT=587`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` (Gmail needs an *app password*, made under the Google account's Security, 2-Step Verification, App passwords) and `EMAIL_FROM`. Then add your address under Settings and test: `cd backend; .\.venv\Scripts\python.exe manage.py send_alerts --test` (one test email) or `send_alerts --demo` (one made-up example of every alert, marked TEST). With `EMAIL_HOST` empty the emails are only printed in the server window.
12. **Reports into Google Drive** (automatic, every 4 weeks). Every day at 3:30 am a task saves three PDFs (Storage, Receiving, Dispatch) for each finished 4-week block, named like `2026-11-01 to 2026-11-28 - Storage.pdf`. A block is only made once, and one missed while the PC was off is made the next time. Blocks are 28 days, Sunday to Saturday, counted from Sunday 1 Nov 2026 (`FIRST_BLOCK_START` in `backend/reports/management/commands/export_reports.py`), so the first PDFs appear on 29 Nov 2026. They are always kept in the `report_exports` folder inside the project (not in git). To also get them into Google Drive, choose one of these extra copies:

    **A. Upload straight to Drive (no desktop app).** One-off setup in Google:
    1. console.cloud.google.com: create a project, turn on the **Google Drive API**.
    2. IAM & Admin, Service Accounts: create one (give it **no project role**), then Keys, Add key, JSON. A key file downloads. It is a secret: never put it in the repo or send it in a message.
    3. In Drive make a folder "Temperature Logger Reports" and share it with the service account's email (`...@...iam.gserviceaccount.com`) as **Editor**.
    4. Save the key file on the orders PC outside the repo, e.g. `C:\TempLoggerSecrets\drive-key.json`.
    5. In `backend\.env` set `GOOGLE_SERVICE_ACCOUNT_FILE=C:\TempLoggerSecrets\drive-key.json` and `GOOGLE_DRIVE_FOLDER_ID=` the last part of the folder's web address (after `/folders/`).
    6. Check it: `cd backend; .\.venv\Scripts\python.exe manage.py export_reports --check` should say it can see the folder. Test an upload with `manage.py export_reports --include-current` (saves the block under way; delete the test files in Drive afterwards).

    **B. Google Drive for desktop (what the orders PC uses).** Put a folder inside Drive in `backend\.env`, e.g. `REPORTS_EXPORT_DIR=G:\My Drive\Temp Logger Reports` (Stream files works, as for the backups). The task below then runs as the same Windows user Drive is signed in under, and files only reach Drive while that user is logged in.

    Either way, finish with: `.\scripts\install_report_export.ps1` (ordinary PowerShell as that Windows user, not administrator), then `.\scripts\export_reports.ps1` and read `backend\logs\export_reports.log`. After pulling, run `pip install -r requirements.txt` (`deploy.ps1` does) because Drive upload needs the Google packages.

## Updating

**Automatic (normal way).** Code is changed on another computer and pushed to `main` on GitHub. Every 5 minutes the "Temperature Logger Auto Deploy" task (made by `install_autostart.ps1`) runs `scripts\auto_deploy.ps1`: it pulls, installs new packages, runs the tests, builds the frontend into a side folder, migrates, swaps the new frontend in and restarts the server, and goes back to the previous version if anything fails. Every deploy, skip and failure is written to `backend\logs\auto_deploy.log`. It skips (and logs why) while the orders PC folder has uncommitted changes or commits not on GitHub, so after changing anything on the orders PC itself, commit **and push**.

**Before pushing, run the tests on Postgres** (`python manage.py test --noinput`), not only with `USE_SQLITE=1`. The orders PC runs them on Postgres, where the never-delete triggers are active; a test that deletes a record passes on SQLite and then blocks every deploy. If a deploy keeps failing, `auto_deploy.log` shows the error and the live app stays on the previous version. Push the fix from the other computer and it goes live by itself. (A fix committed in the orders PC folder itself leaves nothing new on GitHub for auto-deploy to see: then run `.\scripts\deploy.ps1` once.)

**By hand**, on the orders PC:

```
cd C:\Users\<you>\temp-logger
.\scripts\deploy.ps1
```

It pulls, installs packages, runs the tests, builds the frontend into a side folder, migrates the database, swaps the new frontend in, restarts the server, and checks it answers. If anything fails it stops before replacing the running app.

If Claude Code is used on the orders PC, it should read `CLAUDE.md` first. Never run a plain `npx vite build` while the app is live (it replaces the live `dist` folder); `deploy.ps1` builds to `dist-next` for that reason.

## Restoring from a backup

Practise this on a spare database first:

```
createdb -h 127.0.0.1 -U postgres temp_logger_restore_test
pg_restore -h 127.0.0.1 -U postgres -d temp_logger_restore_test D:\Backups\temp-logger\temp_logger_2026-11-02.dump
```
Open the result in pgAdmin and check the readings are there. To restore for real, stop the server, restore into an empty `temp_logger` database, and start it again.

## Where things are

| What | Where |
|---|---|
| Server, keep-alive, auto-deploy, backup and report export logs | `backend\logs\` |
| Database settings and secrets | `backend\.env` (never committed) |
| Backups | `BACKUP_DIR` (local) and `BACKUP_DRIVE_DIR` (Google Drive), both in `backend\.env` |
| Report PDFs | `report_exports\` in the project, plus `REPORTS_EXPORT_DIR` (Google Drive) |
| Port | 8003 (`scripts\run_server.bat`) |
