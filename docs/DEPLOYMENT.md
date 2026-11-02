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
10. **Nightly backup** (2 am). Use a different drive or a synced folder for `-BackupDir` if you can:
    ```
    schtasks /Create /TN "Temperature Logger Backup" /SC DAILY /ST 02:00 /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"$PWD\scripts\backup.ps1\" -BackupDir D:\Backups\temp-logger"
    ```
    Run `scripts\backup.ps1` once by hand and check that a `.dump` file appears. **Test a restore before relying on it** (see below).

11. **Alert emails.** Every 5 minutes (the task `install_autostart.ps1` makes) the app emails the people under *Settings, Alert emails* when: a storage reading is due in 15 minutes and units are not logged, a reading was missed (2 hours after its time), a reading is saved out of limit, or a corrective action has waited 2 hours for a manager. Each alert is sent once. To send real email, put the sending account in `backend\.env`: `EMAIL_HOST` (for Gmail `smtp.gmail.com`, for Microsoft 365 `smtp.office365.com`), `EMAIL_PORT=587`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` (Gmail needs an *app password*, made under the Google account's Security, 2-Step Verification, App passwords) and `EMAIL_FROM`. Then add your address under Settings and test: `cd backend; .\.venv\Scripts\python.exe manage.py send_alerts --test`. With `EMAIL_HOST` empty the emails are only printed in the server window.
12. **Reports into Google Drive** (automatic, every 4 weeks). Every day at 3:30 am a task saves three PDFs (Storage, Receiving, Dispatch) for each finished 4-week block, named like `2026-11-01 to 2026-11-28 - Storage.pdf`. A block is only made once, and one missed while the PC was off is made the next time. Blocks are 28 days, Sunday to Saturday, counted from Sunday 1 Nov 2026 (`FIRST_BLOCK_START` in `backend/reports/management/commands/export_reports.py`), so the first PDFs appear on 29 Nov 2026. They are always kept in the `report_exports` folder inside the project (not in git). To also get them into Google Drive, choose one of these extra copies:

    **A. Upload straight to Drive (no desktop app).** One-off setup in Google:
    1. console.cloud.google.com: create a project, turn on the **Google Drive API**.
    2. IAM & Admin, Service Accounts: create one (give it **no project role**), then Keys, Add key, JSON. A key file downloads. It is a secret: never put it in the repo or send it in a message.
    3. In Drive make a folder "Temperature Logger Reports" and share it with the service account's email (`...@...iam.gserviceaccount.com`) as **Editor**.
    4. Save the key file on the orders PC outside the repo, e.g. `C:\TempLoggerSecrets\drive-key.json`.
    5. In `backend\.env` set `GOOGLE_SERVICE_ACCOUNT_FILE=C:\TempLoggerSecrets\drive-key.json` and `GOOGLE_DRIVE_FOLDER_ID=` the last part of the folder's web address (after `/folders/`).
    6. Check it: `cd backend; .\.venv\Scripts\python.exe manage.py export_reports --check` should say it can see the folder. Test an upload with `manage.py export_reports --include-current` (saves the block under way; delete the test files in Drive afterwards).

    **B. Google Drive for desktop.** Install it on the orders PC, sign in, choose **Mirror files** (not Stream), and put the path of the synced folder in `backend\.env` as `REPORTS_EXPORT_DIR=...`. The scheduled task below must then run as the same Windows user Drive is signed in under.

    Either way, finish with: `.\scripts\install_report_export.ps1` (ordinary PowerShell as that Windows user, not administrator), then `.\scripts\export_reports.ps1` and read `backend\logs\export_reports.log`. After pulling, run `pip install -r requirements.txt` (`deploy.ps1` does) because Drive upload needs the Google packages.

## Updating

After new code is pushed to GitHub, on the orders PC:

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
| Server log, keep-alive log, backup log | `backend\logs\` |
| Database settings and secrets | `backend\.env` (never committed) |
| Backups | the `-BackupDir` you chose |
| Port | 8003 (`scripts\run_server.bat`) |
